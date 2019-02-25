## nspx 0.2-6 (NSP eXtractor) ##

#### extracts nintendo switch software packages (*.nsp-files) ####

<hr/>

Requirements:
- python (2 and 3 both seem to work)

Packaging requirements:
- pyinstaller:		run `pyinstaller --onefile nspx.py`, result will be in "dist/"

Syntax:
- `./nspx.py -lf example.nsp` -	lists contents of example.nsp
- `./nspx.py -xf example.nsp` -	extracts all files from example.nsp into ./example
- `./nspx.py -xf example.nsp icon.jpg` - extracts "icon.jpg" from "example.nsp" into "./example" (can add more names to extract)
- `./nspx.py -sxf example.nsp largefile.nca` - extracts  "largefile.nca" and splits it into 4GB parts, if it is >4GB (WIP, not working yet)
- `./nspx.py -af example.nsp icon.jpg` - creates new archive (cannot append files to existing archive, yet)

Changes:
- in v0.2-6d2:
  - changed 'pfs0.py':
  	- changed logger function requirements:
		def logger_fn( log_level: str, msg: str ) -> any
	- PFS0File contructor now takes a pathname instead of a file object
	- PFS0File constructor now accepts a custom logger function, following above requirements
	- PFS0File constructor now stores filenames in memory, instead of reading it per use
	- PFS0File listfiles changed format list( tuple( file_name: str, file_size: int, file_offset: int ), ... )
	- Added update method to PFS0File, that updates file information
	- renamed a lot of variables
  - functionality remains the same
- in v0.2-6d1:
  - Readded splitting using a rewritten function
- in v0.2-5:
  - Added some docstring and comments to "pfs0.py"
  - removed splitted extracting as it doesn't work yet
- in v0.2-4:
	- Note: I haven't had time to thoroughly test the splitting feature, so there could be some errors within the code still
- in v0.2:
	- cleaned up some code
	- put pfs0 code in its own class
	- switched to optparse
