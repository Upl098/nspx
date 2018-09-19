#!/usr/bin/env python

"""
    Copyright (c) 2018, Alais Mono
    Everyone is permitted to copy and distribute verbatim copies of this license document


    - not the best code I've ever written, but it does the job
    - p.s.: python2/3 both seem to work
"""

import os, sys
from struct import pack as pk, unpack as upk

def main( argc, argv ):
    if argc < 3:
        print( "nspx 0.1-1\n" )
        print( "usage: %s [command] [nsp-file] [<files to extract>]" % argv[0] )
        print( "\nwhere [command] is:\n\tl: list files\n\tx: extract files\n\nfiles will be extracted into a folder\nwith the .nsp-files basename(without extension)" )
        exit(1)
    
    if not os.path.isfile( argv[2] ):
        print( "error: '%s' is not a file!" % argv[2] )
        exit(2)
    
    nspFile = open( argv[2], "rb" )

    magic = nspFile.read( 4 )

    if magic != b'PFS0':
        print( "error: invalid nsp file!\nMagic should be PFS0, but is '%s'" % magic.decode() )
        exit(3)
    
    numberFiles = upk( "<I", nspFile.read( 4 ) )[0]
    headerRest  = upk( "<I", nspFile.read( 4 ) )[0]

    nspFile.read( 4 ) # skip seperator

    fileSpecs = [] # ( "data-offset", "data-size", "name-offset" )
    fileNames = []

    for n in range( numberFiles ):
        doff = upk( "<Q", nspFile.read( 8 ) )[0]
        dsiz = upk( "<Q", nspFile.read( 8 ) )[0]
        noff = upk( "<I", nspFile.read( 4 ) )[0]
        nspFile.read( 4 ) # skip seperator

        fileSpecs.append( ( doff, dsiz, noff ) )
    
    bytesRead = 0

    fileNamesBase = nspFile.tell()

    def getfilename( off ):
        nspFile.seek( fileNamesBase + off )
        fname = b''
        while 1:
            b = nspFile.read( 1 )
            if b == b'\x00':
                break
            fname += b
        return fname.decode()

    for n in range( numberFiles ):
        fname = b''
        while 1:
            b = nspFile.read( 1 )
            bytesRead += 1
            if b == b'\x00':
                break
            fname += b
        fileNames.append( fname.decode() )

    headerSize = nspFile.tell() + headerRest - bytesRead

    if argv[1] == "l":
        print( "Contents of '%s':" % argv[2] )

        padTo = len( max( fileNames, key=len ) ) + 1

        for n in range( numberFiles ):
            print( "\t%s: %d bytes" % ( fileNames[ n ].ljust( padTo ), fileSpecs[ n ][ 1 ] ) )
        exit( 0 )
    elif argv[1] == "x":
        files = argv[3:]

        outpdir = os.path.splitext( argv[2] )[0]

        if not os.path.isdir( outpdir ): os.mkdir( outpdir )

        if len(files) == 0:
            # extract all
            for fspec in fileSpecs:

                fnameloc = getfilename( fspec[ 2 ] )
                print( "Extracting '%s'..." % fnameloc )
                fout = open( os.path.join( outpdir, fnameloc ), "wb" )

                nspFile.seek( fspec[0] + headerSize )
                goal = headerSize + fspec[0] + fspec[1]
                while 1:
                    rest = goal - nspFile.tell()
                    if rest < 4096:
                        fout.write( nspFile.read( rest ) )
                        break
                    else:
                        fout.write( nspFile.read( 4096 ) )
                fout.close()
        else:
            for name in files:
                if not name in fileNames:
                    print( "error: '%s' can't be found in '%s'" % ( name, argv[2] ) )
                    exit( 3 )
                fspec = fileSpecs[ fileNames.index( name ) ]
                
                fout = open( os.path.join( outpdir, name ), "wb" )
                nspFile.seek( fspec[0] + headerSize )
                goal = headerSize + fspec[0] + fspec[1]
                while 1:
                    rest = goal - nspFile.tell()
                    if rest < 4096:
                        fout.write( nspFile.read( rest ) )
                        break
                    else:
                        fout.write( nspFile.read( 4096 ) )
                fout.close()

        print( "Done!" )        


if __name__ == "__main__":
    main( len( sys.argv ), sys.argv )