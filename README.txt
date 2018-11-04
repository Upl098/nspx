nspx 0.2-4 (NSP eXtractor)
	extracts nintendo switch software packages (*.nsp-files)

Requirements:
	python (2 and 3 both seem to work)

Building requirements:
	pyinstaller:		run 'pyinstaller --onefile nspx.py', result will be in dist/

Syntax:
	./nspx.py -lf example.nsp			-	lists contents of example.nsp
	./nspx.py -xf example.nsp			-	extracts all files from example.nsp into ./example
	./nspx.py -xf example.nsp icon.jpg		-	extracts icon.jpg from example.nsp into ./example (can add more names to extract)
	./nspx.py -sxf example.nsp largefile.nca	-	extracts largefile.nca and splits it into 4GB parts, if it is >4GB
	./nspx.py -af example.nsp icon.jpg		-	creates new archive (cannot append files to existing archive, yet)

Changes:
in v0.2-4:
	- Note: I haven't had time to thoroughly test the splitting feature, so there could be some errors within the code still
in v0.2:
	- cleaned up some code
	- put pfs0 code in its own class
	- switched to optparse
