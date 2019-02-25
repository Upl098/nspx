#!/usr/bin/env python3

"""
    Copyright (c) 2018, Alais Mono
    Everyone is permitted to copy and distribute verbatim copies of this license document

    - p.s.: python2/3 both seem to work
"""

import sys, os
import optparse
from shutil import rmtree
from pfs0 import PFS0File

# exit/error codes
SUCCESS       = 0
NO_FILENAME   = 1
NO_SUCH_FILE  = 2
NO_ACTION     = 3
NO_INFILES    = 4
ERROR         = 255

# Globals
TMPDIR         = os.path.abspath( ".nspx.tmp" )
VERSION_STRING = "v0.2-6d2"

def main():
    parser = optparse.OptionParser( "usage: %prog [options] file1 file2 ..." )

    parser.set_defaults( action=0 )

    actions = optparse.OptionGroup( parser, "Actions", "action commands for script" )
    
    actions.add_option( "-x", "--extract", action="store_const", const=1     , dest="action"  , help="Extract all files or specified files" )
    actions.add_option( "-l", "--list"   , action="store_const", const=2     , dest="action"  , help="List all files in archive and their sizes in bytes" )
    actions.add_option( "-a", "--append" , action="store_const", const=3     , dest="action"  , help="Append files specified to archive" )
    actions.add_option( "-v", "--version", action="store_const", const=4     , dest="action"  , help="Display version string")

    parser.add_option_group( actions )

    parser.add_option( "-f", "--file"   , action="store"      , default=None , dest="filename"    , help="Specify archive file to operate on" )
    parser.add_option( "-s", "--split"  , action="store_true" , default=False, dest="should_split", help="Split nca files into 4GB parts for FAT32 filesystem" )
    parser.add_option( "-o", "--outdir" , action="store"      , default=None , dest="outdir"      , help="Optionally set output directory for extraction" )
    parser.add_option( "-q", "--quiet"  , action="store_true" , default=False, dest="silent"      , help="Supress info messages" )

    ( options, args ) = parser.parse_args()

    if options.action == 4:
        sys.stdout.write( "nspx (NSP eXtractor) %s\n" % VERSION_STRING )
        os._exit( SUCCESS )
    elif options.filename == None:
        sys.stdout.write( "Need to specify a filename with '-f'\n" )
        os._exit( NO_FILENAME )
    elif not os.path.isfile( options.filename ) and options.action != 3:
        sys.stdout.write( "There is no such file '%s'\n" % options.filename )
        os._exit( NO_SUCH_FILE )

    if not options.silent: PFS0File.set_logger()

    if options.action == 0:
        sys.stdout.write( "Nothing to do\n" )
        os._exit( NO_ACTION )
    elif options.action == 3:
        if len( args ) == 0:
            sys.stdout.write( "Nothing to do\n" )
            os._exit( NO_INFILES )
        
        for name in args:
            if not os.path.isfile( os.path.abspath( name ) ):
                sys.stdout.write( "No such file '%s'\n" % name )
                os._exit( NO_SUCH_FILE )

        PFS0File.create_pfs0( options.filename, args ).close()
        os._exit( SUCCESS )
    
    try:
        nspFile = PFS0File( options.filename )

        if options.action == 2:
            sys.stdout.write( "Files in '%s':\n" % options.filename )
            
            flist = nspFile.listfiles()

            fnames, fsizes = [ f[ 0 ] for f in flist ], [ str( f[ 1 ] ) for f in flist ]

            maxName = len( max( fnames, key=len ) )
            maxSize = len( max( fsizes, key=len ) )
            
            for n in range( len( fnames ) ):
                sys.stdout.write( "\t%s : %s bytes\n" % ( fnames[ n ].ljust( maxName ), fsizes[ n ].rjust( maxSize ) ) )
            
        elif options.action == 1:

            nspFile.extract_files( args, options.outdir or os.path.splitext( options.filename )[ 0 ], splitFiles=options.should_split )

            if not options.silent: sys.stdout.write( "Done!\n" )

        nspFile.close()

        os._exit( SUCCESS )
    except Exception as ex:
        sys.stdout.write( "%s\n" % repr( ex ) )
        os._exit( ERROR )

if __name__ == "__main__":
    if os.path.isdir( TMPDIR ):
        rmtree( TMPDIR )
    main()
