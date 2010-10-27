#By running "python setup.py py2exe" this script generates a windows stand-alone
#distribution of the Fisheries Explorer

from distutils.core import setup
import py2exe
import matplotlib
import shutil

# Remove the build folder
shutil.rmtree("build", ignore_errors=True)

# do the same for dist folder
shutil.rmtree("dist", ignore_errors=True)

data_files = matplotlib.get_py2exe_datafiles()
data_files += ['license.html','about.html',('images',["images/fishnet.ico","images/seafoodcrc.png",'images/fishnet.png','images/about.png','images/fish.png'])]
dll_excludes = ['libgdk-win32-2.0-0.dll', 'libgobject-2.0-0.dll', 'tcl84.dll',
                'tk84.dll',
                'MSVCP90.dll', 'mswsock.dll', 'powrprof.dll']


excludes = ['_gtkagg' ]

setup(
    windows = [
        {
            "script": "fisheries_gui.py",
            "icon_resources": [(1, "images\\fishnet.ico")],
            #"other_resources": [(24,1,manifest)]
        }
    ],
	options = {"py2exe": {	'excludes': excludes,
							'includes': ['matplotlib.backends.backend_tkagg','unittest','inspect'],
							"dll_excludes": dll_excludes,
#							"compressed": 2,
#                          "optimize": 2,
#                          "bundle_files": 2,
#                          "xref": False,
#                          "skip_archive": False,
#                          "ascii": False,
#                          "custom_boot_script": ''
}
						  },
 data_files=data_files
)
