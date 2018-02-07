#!/usr/bin/env python
# -*- coding: utf-8 -*- #


# Скрипт для обновления версии модуля и всех зависимых от него модулей.
# Если путь до модуля не указан в аргументе скрипта, тогда будет обновлена версия модуля в текущей директории.
#
# cd <module-path>
# <project-dir>/increment-version.py
# ...
# review changes and commit

from subprocess import call, Popen, PIPE, check_output
import os
import re
import sys

getVersionCommand = "mvn org.apache.maven.plugins:maven-help-plugin:2.1.1:evaluate " \
                    "-Dexpression=project.version 2>/dev/null | grep -v '\['"


def getCurrentModuleVersion():
    return check_output(getVersionCommand, shell=True).decode("utf-8").split("\n")[0]


def incrementLastDigit(version):
    digits = version.split(".")
    lastDigit = int(digits[-1])
    digits[-1] = str(lastDigit+1)
    return ".".join(digits)


def isUpdatedVersionInFile(version, file):
    return "<version>" + version + "</version>" in \
           check_output("git diff HEAD --no-ext-diff --unified=0 --exit-code -a --no-prefix {} "
                        "| egrep \"^\\+\"".format(file), shell=True).decode("utf-8")


def runVersionSet(version):
    process = Popen(["mvn", "versions:set", "-DnewVersion="+version, "-DgenerateBackupPoms=false"], stdout=PIPE)
    (output, err) = process.communicate()
    exitCode = process.wait()
    if exitCode is not 0:
        print "Error setting the version"
        exit(1)
    return output, err, exitCode


def addChangedPoms(version, dirsToVisit, visitedDirs):
    changedFiles = check_output(["git", "ls-files", "-m"]) \
        .decode("utf-8").split("\n")
    changedPoms = [f for f in changedFiles if f.endswith("pom.xml")]
    changedDirs = [os.path.dirname(os.path.abspath(f)) for f in changedPoms if isUpdatedVersionInFile(version, f)]
    changedDirs = [d for d in changedDirs if d not in visitedDirs and d not in dirsToVisit]
    print "New dirs to visit:", changedDirs
    return changedDirs


def getVersion(dirToVisit, currentVersion, defaultVersion):
    return raw_input("New version for {}:{} ({}):".format(dirToVisit, currentVersion, defaultVersion))


if __name__ == "__main__":
    visitedDirs = []
    dirsToVisit = []

    if len(sys.argv) > 1:
        fullPath = os.path.abspath(sys.argv[1])
        if not os.path.exists(fullPath):
            print "Error. Directory not exists:", fullPath
            exit(1)
        if not os.path.exists(os.path.join(fullPath, "pom.xml")):
            print "Error. No pom.xml file in dir", fullPath
            exit(1)
        dirsToVisit.append(os.path.abspath(sys.argv[1]))
    else:
        dirsToVisit.append(os.path.abspath(os.getcwd()))

    pattern = re.compile("aggregation root: (.*)")
    while len(dirsToVisit) > 0:
        dirToVisit = dirsToVisit.pop()
        print "Visiting dir", dirToVisit
        os.chdir(dirToVisit)

        currentVersion = getCurrentModuleVersion()
        try:
            defaultVersion = incrementLastDigit(currentVersion)
        except ValueError:
            defaultVersion = ""
        version = getVersion(dirToVisit, currentVersion, defaultVersion)
        while not version.strip():
            if defaultVersion:
                version = defaultVersion
                break
            version = getVersion(dirToVisit, currentVersion, defaultVersion)

        print "New version:", version
        output, err, exitcode = runVersionSet(version)
        rootDir = pattern.search(output).group(1)
        visitedDirs = visitedDirs + [dirToVisit]
        os.chdir(rootDir)
        print "Adding new dirs to visit"
        dirsToVisit = dirsToVisit + addChangedPoms(version, dirsToVisit, visitedDirs)


