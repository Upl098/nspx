import os, sys
import shutil
from struct import pack as pk, unpack as upk
from typing import IO, List, Tuple, Callable

# log_lvl: str = { "info", "warn", "err" }
LOGGER = lambda log_lvl, msg: None

FILE_MAGIC = b'PFS0'
FAT32_MAX_SIZE = 4 * ( 1024 ** 3 ) # 4GB

class PFS0File:
    # ---------------------------------- static methods  ---------------------------------- #

    @staticmethod
    def set_logger( logger_fn: Callable[[str,str],any] = lambda llvl, msg: sys.stdout.write( "[%s]: %s\n" % (llvl, msg) ) ):
        """Sets the default logger function for PFS0File instances to use
        Must accept two strings (log_level & message) where log_level is one of "info", "warn", "err"
        """
        global LOGGER

        LOGGER = logger_fn
    
    @staticmethod
    def create_pfs0( pfs0Name: str, files: List[str] ):
        """Creates/Repacks a pfs0 container and file.
           The file will be located at 'pfs0Name'
           and contain all files specified in 'files'.

           This function will return a new PFS0File instance with a fp
           to the newly created file

           Default logger function will be used
        """

        pfs0Name = os.path.abspath( pfs0Name )

        LOGGER( "info", "Creating file '%s'..." % pfs0Name )

        fp = open( pfs0Name, "wb+" )

        fp.seek( 0 )
        fp.write( PFS0File.__gen_header( files ) )

        for f in files:
            fname = os.path.abspath( f )

            if not os.path.isfile( fname ):
                fp.close()
                os.unlink( pfs0Name )
                LOGGER( "err", "File '%s' doesn't exist! Aborting..." % fname )
                raise Exception( "Error: File '%s' doesn't exist!" % fname )

            fp_in = open( fname, "rb" )

            LOGGER( "info", "Appending '%s'..." % fname )

            while 1:
                chunk = fp_in.read( 4096 )
                if chunk == b'': break
                fp.write( chunk )
            
            fp_in.close()

        fp.close()

        LOGGER( "info", "Done!" )

        return PFS0File( pfs0Name )

    @staticmethod
    def __gen_header( files: List[str] ) -> bytes:
        """ Generates header for pfs0 container.
            'files' is a list of strings containing the paths to all files to be included

            Returns the header as a byte sequence

            Default logger will be used
        """

        number_of_files = len( files )

        LOGGER( "info", "Generating header..." )

        # calculate sizes
        stringTable = '\x00'.join([os.path.basename(file) for file in files])
        headerSize = 0x10 + (number_of_files)*0x18 + len(stringTable)
        remainder = 0x10 - headerSize%0x10

        # add padding to a multible of 0x10
        headerSize += remainder
        
        # get file information
        fileSizes = [os.path.getsize(file) for file in files]
        fileOffsets = [sum(fileSizes[:n]) for n in range(number_of_files)]
        
        # string table calculations
        fileNamesLengths = [len(os.path.basename(file))+1 for file in files] # +1 for the \x00 separator
        stringTableOffsets = [sum(fileNamesLengths[:n]) for n in range(number_of_files)]
        

        # assemble header

        header = b'PFS0'
        header += pk('<I', number_of_files)
        header += pk('<I', len(stringTable)+remainder)
        header += b'\x00\x00\x00\x00'
        
        # add file info
        for n in range(number_of_files):
            header += pk('<Q', fileOffsets[n])
            header += pk('<Q', fileSizes[n])
            header += pk('<I', stringTableOffsets[n])
            header += b'\x00\x00\x00\x00'
        header += stringTable.encode()
        header += remainder * b'\x00'
        
        LOGGER( "info", "header successfully created." )

        return header

    # ---------------------------------- private methods ---------------------------------- # 

    def __init__(self, path: str, logger: Callable[[str, str], any] = None):
        """PFS0File constructor

        Opens a pfs0 container file and reads its header

        Params:
            path: str = path to file
            logger: Callable[[str,str],any] = logger function

        Exceptions:
            FileNotFoundError -> file at 'path' was not found

        logger:
            Any function that takes in two strings (log_level, message)
            where log_level is one of:
                "info"
                "warn"
                "err"
        """
        self.opened = False

        # set the logger function
        self.log = logger if logger != None else LOGGER

        # check if the supplied file-path exists
        if not os.path.isfile( path ):
            self.log( "err", "File '%s' not found! " % path )
            raise FileNotFoundError( "The file '%s' could not be opened!" % path )

        try:
            # read file header
            # 4 bytes file magic
            # 4 bytes uint LE no. of file entries
            # 4 bytes uint LE size of string table in bytes
            # 4 bytes seperator \x00\x00\x00\x00
            # 0x18 * no. of file entries:
            #   8 bytes unsigned long long LE data offset (rel. to body)
            #   8 bytes unsigned long long LE data size
            #   4 bytes uint string table offset
            # var. bytes of NULL-terminated strings

            self.log( "info", "Opening file '%s' for reading..." % path )

            fp = open( path, 'rb' )
            
            fp.seek( 0 )

            # file magic

            magic = fp.read( 4 )

            if magic != FILE_MAGIC:
                err_msg = "Invalid file magic, expected 'PFS0', got: '%s'" % magic.decode()
                self.log( "err", err_msg )
                raise ValueError( err_msg )
        
            
            # sizes and offsets

            self.__number_of_file_entries = upk( "<I", fp.read( 4 ) )[ 0 ] # number of files/file entries in container
            self.__string_table_size      = upk( "<I", fp.read( 4 ) )[ 0 ] # size of string table(filenames) in bytes

            fp.read( 4 ) # skip seperator (4 zero-bytes)

            # 0x10 = current position, 0x18 = size of 1 (one) file entry
            self.__string_table_offset    = 0x10 + 0x18 * self.__number_of_file_entries

            # get offset of file body
            self.__body_offset = self.__string_table_offset + self.__string_table_size

            # file information
            self.__update_file_information( fp )

            fp.seek( 0 )
            self.fp = fp
        except:
            err = sys.exc_info()[ 0 ]
            self.log( "err", "Could not read header:\n\n%s" % err.message or str(err) )
            return None

        self.opened = True 
    
    def __update_file_information( self, fp: IO[bytes] = None ):                    
        if not 'rb' in fp.mode:
            self.log( "err", "invalid file mode, need 'rb', got '%s'" % fp.mode )
            raise ValueError( "Invalid file mode" )

        # store current position
        old_pos = fp.tell()
        fp.seek( 0x10 )

        self.__file_information = []

        for n in range( self.__number_of_file_entries ):
            data_offset   = upk( "<Q", fp.read( 8 ) )[ 0 ] # data offset rel. to pfs0 body
            data_size     = upk( "<Q", fp.read( 8 ) )[ 0 ] # data size
            string_offset = upk( "<I", fp.read( 4 ) )[ 0 ] # string table offset of filename

            self.__file_information.append((
                self.__read_filename( fp, string_offset ), # get filename as string
                data_size,
                data_offset + self.__body_offset           # convert to absolute offset
            ))

            fp.read( 4 ) # skip seperator
        
        # restore fp position
        fp.seek( old_pos )
    
    def __read_filename(self, fp: IO[bytes], offset: int ) -> str:
        if not 'rb' in fp.mode:
            self.log( "err", "invalid file mode, need 'rb', got '%s'" % fp.mode )
            raise ValueError( "Invalid file mode" )
        
        if offset > self.__string_table_size:
            self.log( "err", "str-table offset is to big" )
            raise ValueError( "Invalid string table offset" )

        # store current position
        old_pos = fp.tell()
        fp.seek( self.__string_table_offset + offset )

        fname = b''

        # read a NULL-terminated string
        while 1:
            b = fp.read( 1 )

            if b == b'\x00': break
            fname += b

        # restore fp position
        fp.seek( old_pos )

        # return as str object
        return fname.decode()
    

    # file extraction methods #

    def __extract_file( self, data_offset: int, data_length: int, fp_out: IO[bytes] ) -> bool:
        """Extract one file from pfs0 container"""

        if not self.opened:
            self.log( "err", "file is closed" )
            return False

        if not "w" in fp_out.mode:
            self.log( "err", "invalid file-handle for output file")
            return False

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
            self.log( "err", "Could not extract file! Are we out of space?" )
            return False

        return True
    
    def __extract_split_file( self, data_offset: int, data_length: int, outdir: str ) -> bool:
        """WIP: Splits large files into 4GB parts """

        if not self.opened:
            self.log( "err", "file is closed" )
            return False

        fp = self.fp
        
        # remove old extracted files
        if os.path.isdir( outdir ):
            shutil.rmtree( outdir )

        os.mkdir( outdir )
        
        splitSize = 0xFFFF0000 # 4,294,901,760 bytes
        chunkSize = 0x8000 # 32,768 bytes

        fparts    = int( data_length / splitSize )

        self.log( "info", "Will split file into %d 4GiB parts" % ( fparts + 1 ) )

        fp.seek( data_offset )

        rest = data_length

        for part in range( fparts + 1 ):
            psize = 0

            self.log( "info", "Extracting %d of %d " % ( part + 1, fparts + 1 ) )

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
                self.log( "err", "Could not extract filepart! Are we out of space?" )
                return False

            self.log( "info", "Part %d done! " % ( part + 1 ) )
        
        self.log( "info", "Extracted all parts successfully!" )

        return True

    # ---------------------------------- public methods ---------------------------------- #

    def listfiles( self ) -> List[Tuple[str,int,int]]:
        """Returnes file information

        Format:
            [ ( file_name, file_size, file_offset ), ... ]
        """

        return self.__file_information


    def extract_files( self, fnames: List[str], outdir: str, splitFiles=False ) -> bool:
        """Extracts one or more files from the container into a directory
        """

        # TODO: Maybe create some progress indicator 

        if not self.opened:
            self.log( "err", "file is closed" )
            return False

        fp = self.fp

        # WIP
        if splitFiles == True: 
            self.log( "info", "Will split large files" )
            self.log( "warn", "splitting files is WIP!" )

        outdir = os.path.abspath( outdir )

        # create output directory, iff it does not exist already
        if not os.path.isdir( outdir ):
            self.log( "info", "Creating output directory '%s'" % outdir )
            try:
                os.mkdir( outdir )
            except:
                self.log( "err", "Could not create output directory!" )
                return False
        
        # if no files are specified, assume all files need to be extracted
        if fnames == None or len( fnames ) == 0:
            for f in self.listfiles():
                self.log( "info", "Extracting '%s'" % f[ 0 ] )

                # split files >4GB, iff requested
                if splitFiles == True and f[ 1 ] > FAT32_MAX_SIZE:
                    splitFileDir = os.path.join( outdir, f[ 2 ] )
                    if not self.__extract_split_file( f[ 2 ], f[ 1 ], splitFileDir ):
                        self.log( "err", "failed to extract '%s'" % f[ 0 ] )
                else:
                    outfile = open( os.path.join( outdir, f[ 0 ] ), "wb" )
                    if not self.__extract_file( f[ 2 ], f[ 1 ], outfile ):
                        self.log( "err", "failed to extract '%s'" % f[ 0 ] )
                    outfile.close()
        else:
            # go through all specified files
            for f in self.listfiles():
                # extract existing files, ignore non-existing files
                if not f[ 0 ] in fnames:
                    self.log( "warn", "File '%s' does not exist! continuing..." % f[ 0 ] )
                    continue

                self.log( "info", "Extracting '%s'" % f[ 0 ] )

                if splitFiles == True and f[ 1 ] > FAT32_MAX_SIZE:
                    # >4GB file should be split
                    # WIP: maybe works?
                    splitFileDir = os.path.join( outdir, f[ 0 ] )
                    if not self.__extract_split_file( f[ 2 ], f[ 1 ], splitFileDir ):
                        self.log( "err", "Parted file extraction failed" )
                else:
                    # extract like normal
                    outfile = open( os.path.join( outdir, f[ 0 ] ), "wb" )
                    if not self.__extract_file( f[ 2 ], f[ 1 ], outfile ):
                        self.log( "err", "File extraction failed!" )
                    outfile.close()
        return True
    
    def update( self ) -> bool:
        if not self.opened:
            self.log( "err", "file is closed" )
        
        try:
            self.__update_file_information( self.fp )
            return True
        except ValueError:
            self.log( "err", "update failed" )
            return False

    def close( self ) -> None:
        """Closes file"""

        if not self.opened:
            self.log( "warn", "file not opened!" )
            return None

        self.log( "info", "Closing file." )
        self.fp.close()
        self.opened = False