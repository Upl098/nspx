"""
    Copyright (c) 2018, Alais Mono
    Everyone is permitted to copy and distribute verbatim copies of this license document

    - p.s.: python2/3 both seem to work
"""

import os
import shutil
from struct import pack as pk, unpack as upk
from typing import IO

#            0x10 = 16            = PFS0 (4bytes) + numFiles (4bytes) + str_table_len (4bytes) + unused (4bytes)
# numFiles * 0x18 = numFiles * 24 = data_offset (8bytes) + data_size (8bytes) + str_offset (4bytes) + unused (4bytes)

LOGGER = lambda msg: False

FAT32_MAX_SIZE = 4 * 1024 * 1024 * 1024 # 4GB

class PFS0File:

    @staticmethod
    def set_logger( func: callable[[str], None] ):
        """Sets the logger function
           to 'func'.
        """
        global LOGGER
        LOGGER = func

    @staticmethod
    def create_pfs0( pfs0Name: str, files: List[str] ) -> PFS0File:
        """Creates a pfs0 container and file.
           The file will be located at 'pfs0Name'
           and contain all files specified in 'files'.

           This function will return a new PFS0File instance with a fp
           to the newly created file
        """

        pfs0Name = os.path.abspath( pfs0Name )

        LOGGER( "Creating file '%s'..." % pfs0Name )

        fp = open( pfs0Name, "wb+" )

        fp.seek( 0 )
        fp.write( PFS0File.__gen_header( files ) )

        for f in files:
            fname = os.path.abspath( f )

            if not os.path.isfile( fname ):
                fp.close()
                os.unlink( pfs0Name )
                raise Exception( "Error: File '%s' doesn't exist!" % fname )

            fp_in = open( fname, "rb" )

            LOGGER( "Appending '%s'..." % fname )

            while 1:
                chunk = fp_in.read( 4096 )
                if chunk == b'': break
                fp.write( chunk )
            
            fp_in.close()

        fp.close()

        LOGGER( "Done!" )

        return PFS0File( open( pfs0Name, "rb" ) )


    @staticmethod    
    def __gen_header( argv: List[str] ) -> bytes:
        """ Generates header for pfs0 container.
            'argv' is a list of strings containing the paths to all files to be included

            Returns the header as a byte sequence
        """

        argc = len( argv )

        LOGGER( "Generating header..." )

        stringTable = '\x00'.join([os.path.basename(file) for file in argv])
        headerSize = 0x10 + (argc)*0x18 + len(stringTable)
        remainder = 0x10 - headerSize%0x10

        headerSize += remainder
        
        fileSizes = [os.path.getsize(file) for file in argv]
        fileOffsets = [sum(fileSizes[:n]) for n in range(argc)]
        
        fileNamesLengths = [len(os.path.basename(file))+1 for file in argv] # +1 for the \x00 separator
        stringTableOffsets = [sum(fileNamesLengths[:n]) for n in range(argc)]
        
        header =  b''
        header += b'PFS0'
        header += pk('<I', argc)
        header += pk('<I', len(stringTable)+remainder)
        header += b'\x00\x00\x00\x00'
        
        for n in range(argc):
            header += pk('<Q', fileOffsets[n])
            header += pk('<Q', fileSizes[n])
            header += pk('<I', stringTableOffsets[n])
            header += b'\x00\x00\x00\x00'
        header += stringTable.encode()
        header += remainder * b'\x00'
        
        return header

    def __init__( self, fp: IO[bytes] ):
        """PFS0File constructor
           
           Takes a handle to a pfs0 file in reads its header.
        """

        self.fp = fp

        # tests the file handle for "rb" mode
        if not 'r' in fp.mode:
            raise Exception( "Error: File-handle is not readable" )
        
        if not 'b' in fp.mode:
            raise Exception( "Error: Need binary mode on File-handle" )

        self.closed = False

        # read from the beginning of the file
        fp.seek( 0 )

        magic = fp.read( 4 )

        if magic != b'PFS0':
            raise ValueError( "Error: File magic is invalid (expected: 'PFS0', got: '%s')" % magic )

        # information regarding header size        
        self.__number_of_files      = upk( "<I", fp.read( 4 ) )[ 0 ]
        self.__header_remainder_len = upk( "<I", fp.read( 4 ) )[ 0 ] # string table length
        
        fp.read( 4 )

        # tabe offset containing all filenames
        self.__string_table_base = 0x10 + 0x18 * self.__number_of_files 

        # metadata of files [ ( offset, size, string_table_offset ) ]
        self.__files_meta = []

        for n in range( self.__number_of_files ):
            data_offset   = upk( "<Q", fp.read( 8 ) )[ 0 ]  # offset of file body relative to the body of this file
            data_size     = upk( "<Q", fp.read( 8 ) )[ 0 ]  # size of the file
            string_offset = upk( "<I", fp.read( 4 ) )[ 0 ]  # offset of filename relative to the string table

            self.__files_meta.append( ( data_offset, data_size, string_offset ) )

            fp.read( 4 )    # skip seperator (4 zero-bytes; test if they are zero?)
        
        # the remainder of the header only contains the filenames which we don't need right now
        self.__body_base = fp.tell() + self.__header_remainder_len

    def listfiles( self ) -> List[Tuple[int,int,str]]:
        """Returns a list containing tuples of the files metadata:\n
            [( absolute_data_offset, data_size, filename), ...]
        """

        if self.closed: raise Exception( "File is closed" )

        flist = []

        for f in self.__files_meta:
            flist.append( ( self.__body_base + f[ 0 ], f[ 1 ], self.__read_filename( f[ 2 ] ) ) )
        
        return flist
    
    def __read_filename( self, offset: int ) -> str:
        """Reads a filename from a relative offset from the string table and returns it"""

        if self.closed: raise Exception( "File is closed" )

        self.fp.seek( self.__string_table_base + offset )

        fname = b''

        # read a NULL-terminated string
        while 1:
            b = self.fp.read( 1 )

            if b == b'\x00': break
            fname += b
        
        # return as str object
        return fname.decode()
    
    def __extract_file( self, data_offset: int, data_length: int, fp_out: IO[bytes] ) -> bool:
        """Extract one file from pfs0 container"""

        if self.closed: raise Exception( "File is closed" )

        if not "w" in fp_out.mode:
            raise Exception( "Error: File-Handle for output file is not writeable" )

        self.fp.seek( data_offset )

        goal = data_offset + data_length

        try:
            while 1:
                rest = goal - self.fp.tell()

                if rest < 4096:
                    fp_out.write( self.fp.read( rest ) )
                    break
                else:
                    fp_out.write( self.fp.read( 4096 ) )
        except:
            print( "Could not extract file! Are we out of space?" )
            return False

        return True
    
    def __extract_split_file( self, data_offset: int, data_length: int, outdir: str ) -> bool:
        """WIP: Splits large files into 4GB parts """

        if self.closed: raise Exception( "File is closed" )

        fp = self.fp
        
        # remove old extracted files
        if os.path.isdir( outdir ):
            shutil.rmtree( outdir )

        os.mkdir( outdir )
        
        splitSize = 0xFFFF0000 # 4,294,901,760 bytes
        chunkSize = 0x8000 # 32,768 bytes

        fparts    = int( data_length / splitSize )

        LOGGER( "Will split file into %d 4GiB parts" % ( fparts + 1 ) )

        fp.seek( data_offset )

        rest = data_length

        for part in range( fparts + 1 ):
            psize = 0

            LOGGER( "Extracting %d of %d " % ( part + 1, fparts + 1 ) )

            pname = os.path.join( outdir, '{:02}'.format( part ) )

            try:
                with open( pname, "wb" ) as fpo:
                    if rest > splitSize:
                        while psize < splitSize:
                            fpo.write( fp.read( chunkSize ) )
                            psize += chunkSize
                        rest -= splitSize
                    else:
                        while psize < rest:
                            fpo.write( fp.read( chunkSize ) )
                            psize += chunkSize
            except:
                LOGGER( "Could not extract filepart! Are we out of space?" )
                return False

            LOGGER( "Part %d done! " % ( part + 1 ) )
        
        LOGGER( "Extracted all parts successfully!" )

        return True
    
    def extract_files( self, fnames: List[str], outdir: str, splitFiles=False ) -> bool:
        """Extracts one or more files from the container into a directory
           Warning: splitFiles not implemented yet, don't use
        """

        # TODO: Maybe create some progress indicator 

        if self.closed: raise Exception( "File is closed" )

        fp = self.fp

        # not implemented yet
        if splitFiles == True: LOGGER( "Info: Will split large files" )

        outdir = os.path.abspath( outdir )

        if not os.path.isdir( outdir ):
            LOGGER( "Creating output directory '%s'" % outdir )
            os.mkdir( outdir )
        
        if fnames == None or len( fnames ) == 0: # if no files are specified, extract all files
            for f in self.listfiles():
                LOGGER( "Extracting '%s'" % f[ 2 ] )
                if splitFiles == True and f[ 1 ] > FAT32_MAX_SIZE:
                    splitFileDir = os.path.join( outdir, f[ 2 ] )
                    self.__extract_split_file( f[ 0 ], f[ 1 ], splitFileDir )
                else:
                    outfile = open( os.path.join( outdir, f[ 2 ] ), "wb" )
                    self.__extract_file( f[ 0 ], f[ 1 ], outfile )
                    outfile.close()
        else:
            # go through all specified files
            for f in self.listfiles():
                # extract existing files, ignore non-existing files
                if not f[ 2 ] in fnames:
                    LOGGER( "File '%s' does not exist!" % f[ 2 ] )
                    continue

                LOGGER( "Extracting '%s'" % f[ 2 ] )

                if splitFiles == True and f[ 1 ] > FAT32_MAX_SIZE:
                    # >4GB file should be split
                    # WIP: maybe works?
                    splitFileDir = os.path.join( outdir, f[ 2 ] )
                    assert self.__extract_split_file( f[ 0 ], f[ 1 ], splitFileDir ) is True, "Parted file extraction failed"
                else:
                    # extract like normal
                    outfile = open( os.path.join( outdir, f[ 2 ] ), "wb" )
                    assert self.__extract_file( f[ 0 ], f[ 1 ], outfile ) is True, "File extraction failed!"
                    outfile.close()
        
        return True
    
    def close( self ) -> None:
        """Closes file"""

        LOGGER( "Closing file." )
        self.fp.close()
        self.closed = True
