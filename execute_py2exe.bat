rem Package the Fisheries Explorer
python setup.py py2exe

cd dist
rem Remove unnecessary tcl/tk files (thousands of them!)
rmdir /s /q tcl\tcl8.5\tzdata tcl\tk8.5\demos
del tcl\tk8.5\images\*.eps