import os
from struct import pack as pk, unpack as upk

#            0x10 = 16            = PFS0 (4bytes) + numFiles (4bytes) + str_table_len (4bytes) + unused (4bytes)
# numFiles * 0x18 = numFiles * 24 = data_offset (8bytes) + data_size (8bytes) + str_offset (4bytes) + unused (4bytes)

LOGGER = lambda msg: False

class PFS0File:

    @staticmethod
    def set_logger( func ):
        global LOGGER
        LOGGER = func

    @staticmethod
    def create_pfs0( pfs0Name, files ):

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
    def __gen_header( argv ):
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

    def __init__( self, fp ):
        self.fp = fp

        if not "r" in fp.mode:
            raise Exception( "Error: File-handle is not readable" )
        
        fp.seek( 0 )

        magic = fp.read( 4 ).decode()

        if magic != 'PFS0':
            raise ValueError( "Error: File magic is invalid (expected: 'PFS0', got: '%s')" % magic )
        
        self.__number_of_files      = upk( "<I", fp.read( 4 ) )[ 0 ]
        self.__header_remainder_len = upk( "<I", fp.read( 4 ) )[ 0 ]
        
        fp.read( 4 )

        self.__files_meta_base   = 0x10
        self.__string_table_base = 0x10 + 0x18 * self.__number_of_files 

        self.__files_meta = []

        for n in range( self.__number_of_files ):
            data_offset   = upk( "<Q", fp.read( 8 ) )[ 0 ]
            data_size     = upk( "<Q", fp.read( 8 ) )[ 0 ]
            string_offset = upk( "<I", fp.read( 4 ) )[ 0 ]

            self.__files_meta.append( ( data_offset, data_size, string_offset ) )

            fp.read( 4 )
        
        self.__body_base = fp.tell() + self.__header_remainder_len

    def listfiles( self ):  # contains (1) absolute data offset, (2) data len in bytes, (3) filename as string
        flist = []

        for f in self.__files_meta:
            flist.append( ( self.__body_base + f[ 0 ], f[ 1 ], self.read_filename( f[ 2 ] ) ) )
        
        return flist
    
    def read_filename( self, offset ):
        fp = self.fp

        if not "r" in fp.mode:
            raise Exception( "Error: File-handle is not readable" ) 

        fp.seek( self.__string_table_base + offset )

        fname = b''

        while 1:
            b = fp.read( 1 )

            if b == b'\x00': break
            fname += b
        
        return fname.decode()
    
    def extract_file( self, data_offset, data_length, fp_out ):
        fp = self.fp

        if not "r" in fp.mode:
            raise Exception( "Error: File-handle is not readable" )

        if not "w" in fp_out.mode:
            raise Exception( "Error: File-Handle for output file is not writeable" )

        fp.seek( data_offset )

        goal = data_offset + data_length

        while 1:
            rest = goal - fp.tell()

            if rest < 4096:
                fp_out.write( fp.read( rest ) )
                break
            else:
                fp_out.write( fp.read( 4096 ) )
        
        return True
    
    def extract_files( self, fnames, outdir ):
        fp = self.fp

        if not "r" in fp.mode:
            raise Exception( "Error: File-handle is not readable" )

        outdir = os.path.abspath( outdir )

        if not os.path.isdir( outdir ):
            LOGGER( "Creating output directory '%s'" % outdir )
            os.mkdir( outdir )
        
        if fnames == None or len( fnames ) == 0: # if no files are specified, extract all files
            for f in self.listfiles():
                outfile = open( os.path.join( outdir, f[ 2 ] ), "wb" )
                self.extract_file( f[ 0 ], f[ 1 ], outfile )
                outfile.close()
        else:
            for f in self.listfiles():
                if f[ 2 ] in fnames:
                    LOGGER( "Extracting '%s'" % f[ 2 ] )
                    outfile = open( os.path.join( outdir, f[ 2 ] ), "wb" )
                    self.extract_file( f[ 0 ], f[ 1 ], outfile )
                    outfile.close()
        
        return True
    
    def close( self ):
        LOGGER( "Closing file." )
        self.fp.close()
