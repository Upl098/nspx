nspx 0.2-2 (NSP eXtractor)
	extracts nintendo switch software packages (*.nsp-files)

Requirements:
	python (2 and 3 both seem to work)

Syntax:
	./nspx.py -l -f example.nsp			-	lists contents of example.nsp
	./nspx.py -x -f example.nsp			-	extracts all files from example.nsp into ./example
	./nspx.py -x -f example.nsp icon.jpg		-	extracts icon.jpg from example.nsp into ./example (can add more names to extract)
	./nspx.py -a -f example.nsp icon.jpg		-	creates new archive (cannot append files to existing archive, yet)

Changes:
	- cleaned up some code
	- switched to optparse
