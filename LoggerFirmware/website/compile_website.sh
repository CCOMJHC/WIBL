#!/bin/zsh

JAR=${HOME}/Projects-Extras/WIBL/closure-compiler/closure-compiler-v20231112.jar
#JAR=/usr/share/java/closure-compiler.jar

for file in js/*.js
do
    echo Compiling $file ...
    java -jar $JAR --js $file --js_output_file ${file%.js}_compiled.js
done

python inline_flatten.py

rm js/*_compiled.js

magick favicon.png -resize 64x64 -define icon:auto-resize=64,48,32,16 favicon.ico

mkdir -p ../data/website/images
cp images/* ../data/website/images
cp favicon.ico ../data/website

exit 0
