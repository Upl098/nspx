#!/usr/bin/env python3

"""
    Copyright (c) 2018, Alais Mono
    Everyone is permitted to copy and distribute verbatim copies of this license document


    - not the best code I've ever written, but it does the job
    - p.s.: python2/3 both seem to work
"""

import sys, os
import optparse
from struct import pack as pk, unpack as upk
from shutil import rmtree

# exit/error codes
SUCCESS       = 0
NO_FILENAME   = 1
NO_SUCH_FILE  = 2
NO_ACTION     = 3
INVALID_MAGIC = 4
NO_INFILES    = 5
UNIMPLEMENTED = 6

TMPDIR = os.path.abspath( ".nspx.tmp" )

def gen_header(argc, argv):
    stringTable = '\x00'.join([os.path.basename(file) for file in argv[1:]])
    headerSize = 0x10 + (argc-1)*0x18 + len(stringTable)
        #            0x10 = 16            = PFS0 (4bytes) + numFiles (4bytes) + str_table_len (4bytes) + unused (4bytes)
        # numFiles * 0x18 = numFiles * 24 = data_offset (8bytes) + data_size (8bytes) + str_offset (4bytes) + unused (4bytes)
    remainder = 0x10 - headerSize%0x10
    headerSize += remainder
    
    fileSizes = [os.path.getsize(file) for file in argv[1:]]
    fileOffsets = [sum(fileSizes[:n]) for n in range(argc-1)]
    
    fileNamesLengths = [len(os.path.basename(file))+1 for file in argv[1:]] # +1 for the \x00 separator
    stringTableOffsets = [sum(fileNamesLengths[:n]) for n in range(argc-1)]
    
    header =  b''
    header += b'PFS0'
    header += pk('<I', argc-1)
    header += pk('<I', len(stringTable)+remainder)
    header += b'\x00\x00\x00\x00'
    
    for n in range(argc-1):
        header += pk('<Q', fileOffsets[n])
        header += pk('<Q', fileSizes[n])
        header += pk('<I', stringTableOffsets[n])
        header += b'\x00\x00\x00\x00'
    header += stringTable.encode()
    header += remainder * b'\x00'
    
    return header

def mk_nsp( options, args ):
    global TMPDIR
    fname = options.filename

    if os.path.isfile( fname ):
        print( "Not supported, yet." )
        os._exit( UNIMPLEMENTED )
    else:
        # create new archive with files
        if not options.silent: print( "Creating new archive '%s'" % fname )
        nspFile = open( os.path.abspath( fname ), "wb" )
        nspFile.seek( 0 )

        if not options.silent: print( "Generating header..." )
        nspFile.write( gen_header( len( args ) + 1, [ "buffer" ] + args ) )

        for name in args:
            if not options.silent: print( "Appending '%s'" % os.path.basename( name ) )
            with open( os.path.abspath( name ), "rb" ) as f:
                while 1:
                    chunk = f.read( 4096 )
                    if chunk == b'': break
                    nspFile.write( chunk )
        
        nspFile.close() 

    if not options.silent: print( "Done!" )
    os._exit( SUCCESS )


def read_fspecs( fp, base, numFiles ):
    fspecs = []

    fp.seek( base )

    for n in range( numFiles ):
        data_offset = upk( "<Q", fp.read( 8 ) )[ 0 ]
        data_size   = upk( "<Q", fp.read( 8 ) )[ 0 ]
        name_offset = upk( "<I", fp.read( 4 ) )[ 0 ]

        fspecs.append( ( data_offset, data_size, name_offset ) )

        fp.read( 4 )
    
    return fspecs

def read_filename( fp, offset ):
    fp.seek( offset )

    fname = b''

    while 1:
        b = fp.read( 1 )
        if b == b'\x00': break
        fname += b
    
    return fname.decode()

def extract_file( fp_in, outfile, base, length ):
    fp_in.seek( base )

    goal = base + length

    fp_out = open( outfile, "wb" )

    while 1:
        rest = goal - fp_in.tell()

        if rest < 4096:
            fp_out.write( fp_in.read( rest ) )
            break
        else:
            fp_out.write( fp_in.read( 4096 ) )
    
    fp_out.close()

def main( argv, ret_results=False ):
    parser = optparse.OptionParser( "usage: %prog [options] file1 file2 ..." )

    parser.set_defaults( action=0 )

    actions = optparse.OptionGroup( parser, "Actions", "action commands for script" )
    
    actions.add_option( "-x", "--extract", action="store_const", const=1     , dest="action"  , help="Extract all files or specified files" )
    actions.add_option( "-l", "--list"   , action="store_const", const=2     , dest="action"  , help="List all files in archive and their sizes in bytes" )
    actions.add_option( "-a", "--append" , action="store_const", const=3     , dest="action"  , help="Append files specified to archive" )
    actions.add_option( "-v", "--version", action="store_const", const=4     , dest="action"  , help="Display version string")

    parser.add_option_group( actions )

    parser.add_option( "-f", "--file"   , action="store"      , default=None, dest="filename", help="Specify archive file to operate on" )
    parser.add_option( "-o", "--outdir" , action="store"      , default=None, dest="outdir"  , help="Optionally set output directory for extraction" )
    parser.add_option( "-s", "--silent" , action="store_true" , default=False, dest="silent" , help="Supress info messages" )

    ( options, args ) = parser.parse_args( argv )

    if options.action == 4:
        print( "nspx (NSP eXtractor) v0.2-2" )
        os._exit( SUCCESS )
    elif options.filename == None:
        print( "Need to specify a filename with '-f'" )
        os._exit( NO_FILENAME )
    elif not os.path.isfile( options.filename ) and options.action != 3:
        print( "There is no such file '%s'" % options.filename )
        os._exit( NO_SUCH_FILE )

    if options.action == 0:
        print( "Nothing to do" )
        os._exit( NO_ACTION )
    elif options.action == 3:
        if len( args ) == 0:
            print( "Nothing to do" )
            os._exit( NO_INFILES )
        
        for name in args:
            if not os.path.isfile( os.path.abspath( name ) ):
                print( "No such file '%s'" % name )
                os._exit( NO_SUCH_FILE )

        mk_nsp( options, args )
        os._exit( SUCCESS )
    
    fspecs_base = 0 # base of fspecs
    stable_base = 0 # base of string table
    body_base   = 0 # base of body

    nspFile = open( os.path.abspath( options.filename ), "rb" )
    nspFile.seek( 0 )

    if nspFile.read( 4 ) != b'PFS0':
        print( "Invalid file magic." )
        os._exit( INVALID_MAGIC )

    numFiles   = upk( "<I", nspFile.read( 4 ) )[ 0 ] # number of files in archive
    stableSize = upk( "<I", nspFile.read( 4 ) )[ 0 ] # size of string table

    nspFile.read( 4 ) # skip seperator

    fspecs_base = nspFile.tell()

    fspecs = read_fspecs( nspFile, fspecs_base, numFiles )

    stable_base = nspFile.tell()
    body_base   = stable_base + stableSize

    if options.action == 2:
        if ret_results != True: print( "Files in '%s':" % options.filename )
        
        # store info about name, size for pretty printing
        fnames, fsizes = [], []

        for fspec in fspecs:
            fnames.append( read_filename( nspFile, stable_base + fspec[ 2 ] ) )
            fsizes.append( str( fspec[ 1 ] ) )

        if ret_results == True:
            return nspFile, fspecs, fnames

        maxName = len( max( fnames, key=len ) )
        maxSize = len( max( fsizes, key=len ) )
        
        for n in range( len( fnames ) ):
            print( "\t%s : %s bytes" % ( fnames[ n ].ljust( maxName ), fsizes[ n ].rjust( maxSize ) ) )
        
    elif options.action == 1:
        outdir = os.path.abspath( options.outdir ) if options.outdir != None else os.path.abspath( os.path.splitext( options.filename )[ 0 ] )
        if not os.path.isdir( outdir ):
            if not options.silent: print( "Creating output directory '%s'" % outdir )
            os.mkdir( outdir )

        if len( args ) > 0:
            for fspec in fspecs:
                fname = read_filename( nspFile, stable_base + fspec[ 2 ] )
                if fname in args:
                    if not options.silent: print( "Extracting file '%s'" % fname )
                    extract_file( nspFile, os.path.join( os.path.abspath( "." ), outdir, fname ), body_base + fspec[ 0 ], fspec[ 1 ] )
        else:
            for fspec in fspecs:
                fname = read_filename( nspFile, stable_base + fspec[ 2 ] )
                if not options.silent: print( "Extracting file '%s'" % fname )
                extract_file( nspFile, os.path.join( os.path.abspath( "." ), outdir, fname ), body_base + fspec[ 0 ], fspec[ 1 ] )
            
        if not options.silent: print( "Done!" )
        if ret_results == True: return

    nspFile.close()

    os._exit( SUCCESS )

if __name__ == "__main__":
    if os.path.isdir( TMPDIR ):
        rmtree( TMPDIR )
    main( sys.argv )
