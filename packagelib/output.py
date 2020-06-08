from sys import stderr, stdout

ENDC = "\033[0m"
FAIL = "\033[91m"
INFO = "\033[34m"
SUCCESS = "\033[0m"


def error(msg):
    stderr.write("%s%s%s\n" % (FAIL, msg, ENDC))


def info(msg):
    stdout.write("%s%s%s\n" % (INFO, msg, ENDC))


def question(msg):
    info("[?]\t%s" % msg)


def success(msg):
    stdout.write("%s%s%s\n" % (SUCCESS, msg, ENDC))
