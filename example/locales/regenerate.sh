for po in `find . -iname "*.po"`
do
    src_f="${po}"
    tgt_f="`dirname ${po}`/test.mo"
    echo formating ${po} to ${tgt_f}
    msgfmt ${src_f} -o ${tgt_f}
done
