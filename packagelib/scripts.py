link_config = """
function link_config()
{
    echo "Creating symlinks depending on server location."
    # urcime, jestli jsme dev, nebo prod

    local location

    h=`hostname --fqdn`
    fallbacks=(dev test prod)
    if [[ $h == *"test"* ]]
    then
        location="test"
        fallbacks=(prod)
    elif [[ $h == *"cas"* ]]
    then
        location="prod"
        fallbacks=""
    elif [[ $h == *"nag"* ]]
    then
        location="prod"
        fallbacks=""
    elif [[ $h == *"router\-read"* ]]
    then
        location="prod"
        fallbacks=""
    elif [[ $h == *"darky"* ]]
    then
        location="darky"
    elif [[ $h == *"koldaj"* ]]
    then
        location="koldaj"
    elif [[ $h == *"ondrak"* ]]
    then
        location="ondrak"
    elif [[ $h == *"kubac"* ]]
    then
        location="kubac"
    elif [[ $h == *"tymserver"* ]]
    then
        location="tymserver"
    elif [[ $h == *"kubac"* ]]
    then
        location="kubac"
    elif [[ $h == *"radek"* ]]
    then
        location="radek"
    else
        location="dev"
        fallbacks=(test prod)
    fi

    echo  "Rozhoduje se pouze mezi dev, test a prod, vybral jsem: ${location}"

    # nalinkujeme vsechny potrebne konfiguraky
    for conf in "$@"; do
        echo "Checking conffile ${conf}"
        # vyrobime jmeno linku (bez .prod)
        linkname=`echo "${conf}" | sed 's/\.prod\././'|sed 's/\.prod$//'`

        echo "Link will be to ${linkname}"

        # vyrobime cestu ke spravnemu konfigu (.prod. nahradi za .dev. nebo za
        # .prod.) a vezmeme jen basename
        linkdest=""
        for loc in $location ${fallbacks[*]}
        do
            linkdest=`echo "${conf}" | sed "s/\.prod\./.${loc}./" | sed "s/\.prod$/.${loc}/"`
            echo "Gonna check configfile $linkdest"
            if ! test -f "${linkdest}"; then
                echo "Config not found!"
                linkdest=""
            else
                break
            fi
        done
        if [ -z "$linkdest" ]
        then
            echo "CONFIGFILE ${linkdest} has no variant to be linked!!!!" >&2
        else
            linkdest=`basename "$linkdest"`

            if test -f "${linkname}" && ! test -h "${linkname}"; then
                echo "Found non-symlink config $conf... backing up."
                cp -va "${linkname}" "$conf.old"
            fi

            echo ln -sf "${linkdest}" "${linkname}"
            ln -sf "${linkdest}" "${linkname}"
        fi
    done
}
"""

upgrade_pip_package = """
function upgrade_pip_package()
{
    package=$1
    minversion=$2
    installed_version=`pip3 freeze|grep -i "^${package}=="|cut -d "=" -f3`
    if [ "x" == "x${installed_version}" ]
    then
        # no version installed
        echo "no version of $package installed => installing"
        pip3 install ${package}==${minversion}
    else
        #instaled
        if [ "x${minversion}" != "x${installed_version}" ]
        then
            echo "version in not the same checking upgrade $package"
            installed_major=`echo "${installed_version}" | cut -d '.' -f 1`
            requested_major=`echo "${minversion}" | cut -d '.' -f 1`
            if [ "$installed_major" -gt "$requested_major" ]
            then
                echo "already installed newer version of ${package}. Keeping version:${installed_version}"
                return
            fi
            if [ "$installed_major" == "${requested_major}" ]
            then
                # stejna major - otestuj minor
                installed_minor=`echo "${installed_version}" | cut -d '.' -f 2`
                requested_minor=`echo "${minversion}" | cut -d '.' -f 2`
                if [ "$installed_minor" -gt "$requested_minor" ]
                then
                    echo "already installed newer version of ${package}. Keeping version:${installed_version}"
                    return
                fi
                if [ "$installed_minor" == "${requested_minor}" ]
                then
                    # stejna minor - otestuj build
                    installed_build=`echo "${installed_version}" | cut -d '.' -f 3`
                    requested_build=`echo "${minversion}" | cut -d '.' -f 3`
                    if [ "$installed_build" -gt "$requested_build" ]
                    then
                        echo "already installed newer version of ${package}. Keeping version:${installed_version}"
                        return
                    fi
                    # tady neni potreba kontrolovat stejnou verzi protoze
                    # to uz je vyloucene driv
                fi  # minor ==
            fi  # major ==
            echo "installed ${installed_version} version => gonna upgrade to ${minversion}"
            pip3 uninstall -y ${package}
            pip3 install --upgrade ${package}==${minversion}
        else
            echo "version is the same - not upgrading $package"
        fi
    fi
}
"""
