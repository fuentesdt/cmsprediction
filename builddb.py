import sqlite3
import time
import dicom
import subprocess,re,os
import ConfigParser

def parse_findscu(out):
    """
      parse the findscu output
    """
    resp=[]
    res_tags={}
    tg=re.compile("([0-9a-fA-F]{4}),([0-9a-fA-F]{4})");
    val=re.compile("\[(.*)\]");
 
    for l in out.split('\n'):
        if l.startswith("E: "):
            raise RuntimeError
        if l.startswith("W: "):
            l=l[3:];
        
        # print "|%s|" % l
    
        if l.endswith('----'):
            if not res_tags == {}:
                resp.append(res_tags)
            res_tags={}
            continue
        
        s=tg.search(l[1:10])
        if s is not None:
           s2=val.search(l[15:]) 
           if s2 is not None:
               res_tags[s.group(0)]=s2.group(1).decode('utf8','ignore')
      
    resp.append(res_tags) 
    return resp

####################################################################################################################
# build data base from CSV file
def GetDataDictionary():
  import csv
  CSVDictionary = {}
  with open('adrenal/BlindedACCgreaterthan4cm.csv', 'r') as csvfile:
      reader = csv.reader(csvfile, delimiter=',')
      rawaccdata = [row for row in reader]
  with open('adrenal/BlindedACAgreaterthan4cm.csv', 'r') as csvfile:
      reader = csv.reader(csvfile, delimiter=',')
      rawacadata = [row for row in reader]
  for rawdata in [rawacadata ,rawaccdata]:
    header = rawdata.pop(0)
    for row in rawdata:
      SubjectID  = int(row[ header.index('MRN') ])
      accession  = int(row[ header.index('accession')   ])
      sizeinfo   = row[ header.index("size" ) ]
      CSVDictionary[SubjectID] =  { 'accession':[accession] ,'size':sizeinfo, 'dataid':'adrenal'   }

  with open('chemoreponse/initialcases.csv', 'r') as csvfile:
      reader = csv.reader(csvfile, delimiter=',')
      rawhccdata = [row for row in reader]
      for rawdata in [rawhccdata ]:
        header = rawdata.pop(0)
        for row in rawdata:
          SubjectID  = int(row[ header.index('MRN') ])
          baselineaccession  = int(row[ header.index('baselineaccession')   ])
          postaccession      = int(row[ header.index('postaccession')   ])
          CSVDictionary[SubjectID] =  { 'accession':[baselineaccession, postaccession ], 'dataid':'chemo'}
  
  return CSVDictionary 

## Borrowed from
## $(SLICER_DIR)/CTK/Libs/DICOM/Core/Resources/dicom-schema.sql
## 
## --
## -- A simple SQLITE3 database schema for modelling locally stored DICOM files
## --
## -- Note: the semicolon at the end is necessary for the simple parser to separate
## --       the statements since the SQlite driver does not handle multiple
## --       commands per QSqlQuery::exec call!
## -- ;
## TODO note that SQLite does not enforce the length of a VARCHAR. 
## TODO (9) What is the maximum size of a VARCHAR in SQLite?
##
## TODO http://www.sqlite.org/faq.html#q9
##
## TODO SQLite does not enforce the length of a VARCHAR. You can declare a VARCHAR(10) and SQLite will be happy to store a 500-million character string there. And it will keep all 500-million characters intact. Your content is never truncated. SQLite understands the column type of "VARCHAR(N)" to be the same as "TEXT", regardless of the value of N.
initializedb = """
DROP TABLE IF EXISTS 'Images' ;
DROP TABLE IF EXISTS 'Patients' ;
DROP TABLE IF EXISTS 'Series' ;
DROP TABLE IF EXISTS 'Studies' ;
DROP TABLE IF EXISTS 'Directories' ;

CREATE TABLE 'Images' (
 'SOPInstanceUID' VARCHAR(64) NOT NULL,
 'Filename' VARCHAR(1024) NOT NULL ,
 'SeriesInstanceUID' VARCHAR(64) NOT NULL ,
 'InsertTimestamp' VARCHAR(20) NOT NULL ,
 PRIMARY KEY ('SOPInstanceUID') );
CREATE TABLE 'Patients' (
 'PatientsUID' INT PRIMARY KEY NOT NULL ,
 'StdOut'     varchar(1024) NULL ,
 'StdErr'     varchar(1024) NULL ,
 'ReturnCode' INT   NULL ,
 'FindStudiesCMD' VARCHAR(1024)  NULL );
CREATE TABLE 'Series' (
 'SeriesInstanceUID' VARCHAR(64) NOT NULL ,
 'StudyInstanceUID' VARCHAR(64) NOT NULL ,
 'Modality'         VARCHAR(64) NOT NULL ,
 'SeriesDescription' VARCHAR(255) NULL ,
 'StdOut'     varchar(1024) NULL ,
 'StdErr'     varchar(1024) NULL ,
 'ReturnCode' INT   NULL ,
 'MoveSeriesCMD'    VARCHAR(1024) NULL ,
 PRIMARY KEY ('SeriesInstanceUID','StudyInstanceUID') );
CREATE TABLE 'Studies' (
 'StudyInstanceUID' VARCHAR(64) NOT NULL ,
 'PatientsUID' INT NOT NULL ,
 'StudyDate' DATE NULL ,
 'StudyTime' VARCHAR(20) NULL ,
 'AccessionNumber' INT NULL ,
 'StdOut'     varchar(1024) NULL ,
 'StdErr'     varchar(1024) NULL ,
 'ReturnCode' INT   NULL ,
 'FindSeriesCMD'    VARCHAR(1024) NULL ,
 'StudyDescription' VARCHAR(255) NULL ,
 PRIMARY KEY ('StudyInstanceUID') );

CREATE TABLE 'Directories' (
 'Dirname' VARCHAR(1024) ,
 PRIMARY KEY ('Dirname') );
"""

mrnList = GetDataDictionary()
#print mrnList
nsize = len(mrnList )

#FIXME global vars
configini = ConfigParser.SafeConfigParser({})
configini.read('./config.ini')
ip   = configini.get('server','ip'  )
port = configini.get('server','port')
aec  = configini.get('server','aec' )
aet  = configini.get('server','aet' )


from optparse import OptionParser
parser = OptionParser()
parser.add_option( "--initialize",
                  action="store_true", dest="initialize", default=False,
                  help="build initial sql file ", metavar = "BOOL")
parser.add_option( "--builddb",
                  action="store_true", dest="builddb", default=False,
                  help="build db ", metavar = "BOOL")
parser.add_option( "--querydb",
                  action="store_true", dest="querydb", default=False,
                  help="build query commands ", metavar = "BOOL")
parser.add_option( "--convert",
                  action="store_true", dest="convert", default=False,
                  help="convert dicom to nifti", metavar = "BOOL")
parser.add_option( "--movescu",
                  action="store_true", dest="movescu", default=False,
                  help="build movescu makefile ", metavar = "BOOL")

(options, args) = parser.parse_args()
#############################################################
# build initial sql file 
#############################################################
if (options.initialize ):
  # build new database
  os.system('rm ./pacsquery.sql')
  tagsconn = sqlite3.connect('./pacsquery.sql')
  for sqlcmd in initializedb.split(";"):
     tagsconn.execute(sqlcmd )
#############################################################
# build db
#############################################################
elif (options.builddb ):
  tagsconn = sqlite3.connect('./pacsquery.sql')
  cursor = tagsconn.cursor()
  # add mrn 
  #for iddata,mrn in enumerate(mrnList[:10]) :
  for iddata,mrn in enumerate(mrnList) :
    # TODO use case logic ??
    PatientSelectCMD ="""
    select case when exists( select * from Patients where PatientsUID = 314) then (PatientsUID)    else 314   end from Patients;
    select
     case when exists( select * from Patients where PatientsUID = (?)) then (PatientsUID)    else (?)   end,
     case when exists( select * from Patients where PatientsUID = (?)) then (StdOut)         else  NULL end,
     case when exists( select * from Patients where PatientsUID = (?)) then (StdErr)         else  NULL end,
     case when exists( select * from Patients where PatientsUID = (?)) then (ReturnCode)     else  -1   end, 
     case when exists( select * from Patients where PatientsUID = (?)) then (FindStudiesCMD) else (?)   end  
    from Patients;
    """
    # build search commands
    FindStudiesCMD = "findscu  -P  -k 0008,0052=STUDY -k 0010,0020=%d -aet %s -aec %s  %s %s  -k 0020,000d -k 0008,1030 -k 0008,0020 -k 0008,0050 " % (mrn,aet,aec,ip,port)
    # check if id exists
    defaultpatiententry=(mrn,-1,FindStudiesCMD)
    cursor.execute('insert or ignore into Patients (PatientsUID,ReturnCode,FindStudiesCMD) values (?,?,?);' , defaultpatiententry);tagsconn.commit()
    cursor.execute(' select * from Patients where PatientsUID = (?)   ;' , (mrn,) )
    (PatientsUID,StudyStdOut,StudyStdErr,StudyReturnCode,FindStudiesCMD) =  cursor.fetchone()
    if StudyReturnCode != 0 :
       studychild = subprocess.Popen(FindStudiesCMD,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
       (StudyStdOut,StudyStdErr) = studychild.communicate()
       try:
         studydictionary = parse_findscu(StudyStdErr)
         StudyReturnCode = studychild.returncode
         # replace return code and output
         dhtableentry=(mrn,unicode(StudyStdOut),unicode(StudyStdErr),StudyReturnCode,FindStudiesCMD)
         tagsconn.execute('replace into Patients (PatientsUID,StdOut,StdErr,ReturnCode,FindStudiesCMD) values (?,?,?,?,?);' , dhtableentry)
       except RuntimeError:
         studydictionary = {}
         StudyReturnCode = -1
    else:
       studydictionary = parse_findscu(StudyStdErr)
    # search for series in study
    for study in  studydictionary:
      studyuidKey = '0020,000d'
      print "\n study",iddata,nsize,StudyReturnCode,FindStudiesCMD, study
      if studyuidKey in study:
        studyuid = study[studyuidKey ]
        # check for existing study uid
        sqlStudyList = [ xtmp for xtmp in tagsconn.execute(' select * from Studies where StudyInstanceUID = (?)   ;' , (studyuid,))]
        if len( sqlStudyList ) == 0 :
          try: 
            StudyDescription = study[ '0008,1030' ]
          except: 
            StudyDescription = None
          try: 
            StudyDate = study[ '0008,0020' ]
          except: 
            StudyData = None
          try: 
            AccessionNumber = int( study[ '0008,0050' ] )
          except: 
            AccessionNumber = None
          # build search series commands
          FindSeriesCMD = "findscu -S  -k 0008,0052=SERIES  -aet %s -aec %s %s %s -k 0020,000D=%s -k 0020,000E -k 0008,0060 -k 0010,0020=%d -k 0008,103e " %(aet,aec,ip,port,studyuid,mrn)
          serieschild = subprocess.Popen(FindSeriesCMD,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
          (SeriesStdOut,SeriesStdErr) = serieschild.communicate()
          SeriesReturnCode = serieschild.returncode
          # insert return code and output
          try:
            seriesdictionary=parse_findscu(SeriesStdErr)
          except RuntimeError:
            seriesdictionary = {}
            SeriesReturnCode = -1
          dhtableentry=(studyuid , mrn,  StudyDate , None, AccessionNumber, unicode(SeriesStdOut),unicode(SeriesStdErr.decode('utf8','ignore')),SeriesReturnCode , FindSeriesCMD, StudyDescription)
          tagsconn.execute('insert into Studies (StudyInstanceUID, PatientsUID, StudyDate, StudyTime, AccessionNumber, StdOut, StdErr, ReturnCode,  FindSeriesCMD, StudyDescription) values (?,?,?,?,?,?,?,?,?,?);' , dhtableentry)
        elif len( sqlStudyList ) == 1 :
          (StudyInstanceUID, PatientsUID, StudyDate, StudyTime, AccessionNumber, SeriesStdOut, SeriesStdErr, SeriesReturnCode,  FindSeriesCMD, StudyDescription) = sqlStudyList[0]
          # retry if failed last time
          if SeriesReturnCode != 0 :
            serieschild = subprocess.Popen(FindSeriesCMD,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            (SeriesStdOut,SeriesStdErr) = serieschild.communicate()
            SeriesReturnCode = serieschild.returncode
          try:
            seriesdictionary=parse_findscu(SeriesStdErr)
          except RuntimeError:
            seriesdictionary = {}
            SeriesReturnCode = -1
          dhtableentry=(StudyInstanceUID, PatientsUID, StudyDate, StudyTime, AccessionNumber, unicode(SeriesStdOut), unicode(SeriesStdErr.decode('utf8','ignore')), SeriesReturnCode,  FindSeriesCMD, StudyDescription) 
          tagsconn.execute('replace into Studies (StudyInstanceUID, PatientsUID, StudyDate, StudyTime, AccessionNumber, StdOut, StdErr, ReturnCode,  FindSeriesCMD, StudyDescription) values (?,?,?,?,?,?,?,?,?,?);' , dhtableentry)
        else:
          print "more than one entry ? studyUID should be unique? ", sqlStudyList 
          raise RuntimeError
        for series  in seriesdictionary:
          print series 
          seriesuidKey = '0020,000e'
          if (seriesuidKey in series) :
            seriesuid = series[seriesuidKey]
            # check for existing study uid
            sqlSeriesList = [ xtmp for xtmp in tagsconn.execute(' select * from Series where SeriesInstanceUID = (?) and StudyInstanceUID = (?)   ;' , (seriesuid ,studyuid) )]
            if len(sqlSeriesList ) == 0 :
              try: 
                SeriesDescription = series[ '0008,103e' ]
              except: 
                SeriesDescription = None
              try: 
                Modality = series[ '0008,0060' ]
              except: 
                Modality = None
              MoveSeriesCMD = "movescu -v -S  -k 0008,0052=SERIES  -aet %s -aec %s %s %s -k 0020,000D=%s -k 0020,000e=%s -k 0010,0020=%d " %(aet,aec,ip,port,studyuid,seriesuid,mrn)
              # TODO - 'NM' 'XA' Modality giving integrity errors ? 
              if Modality not in[ 'NM','XA']:
                dhtableentry=(seriesuid , studyuid, Modality, SeriesDescription ,MoveSeriesCMD )
                tagsconn.execute('insert into Series (SeriesInstanceUID,StudyInstanceUID,Modality,SeriesDescription,MoveSeriesCMD) values (?,?,?,?,?);' , dhtableentry)
            elif len(sqlSeriesList ) == 1 :
              pass
            else:
              print "more than one entry ? seriesUID should be unique? ", seriesuid 
              raise RuntimeError
          #except KeyError as inst:
          else:
            print "error reading: ", series  ,seriesdictionary
            raise RuntimeError
      else:
        print "?? error reading: study ",study
        raise RuntimeError
    # commit per patient
    tagsconn.commit()
#############################################################
# transfer data
#############################################################
elif (options.querydb ):
  tagsconn = sqlite3.connect('./pacsquery.sql')
  
  # get adrenal list
  AdrenalAccessionList = []
  for iddata,(mrn,mrndata) in enumerate(mrnList.iteritems()) :
    if mrndata['dataid'] == 'adrenal':
      for accessionnum in mrndata['accession']:
         AdrenalAccessionList.append( "AccessionNumber = %d" % accessionnum )
  # search studies for accession number
  sqlStudyListAdrenal = [ "StudyInstanceUID = '%s'" % xtmp[0] for xtmp in tagsconn.execute(" select StudyInstanceUID from Studies where %s " % " or ".join(AdrenalAccessionList))]

  # get chemo list
  ChemoAccessionList = []
  for iddata,(mrn,mrndata) in enumerate(mrnList.iteritems()) :
    if mrndata['dataid'] == 'chemo':
      for accessionnum in mrndata['accession']:
         ChemoAccessionList.append( "AccessionNumber = %d" % accessionnum )
  # search studies for accession number
  sqlStudyListChemo = [ "se.StudyInstanceUID = '%s'" % xtmp[0] for xtmp in tagsconn.execute(" select StudyInstanceUID from Studies where %s " % " or ".join(ChemoAccessionList))]

  #for sqlStudyList in  [sqlStudyListAdrenal ,sqlStudyListChemo ]:
  for sqlStudyList in  [sqlStudyListChemo ]:
    #Search the series description of data of interest
    querymovescu =  " select * from Series se where se.SeriesDescription not like '%%%%scout%%%%' and  (%s);" % " or  ".join(sqlStudyList)
    print "querymovescu "
    print querymovescu 
    print " "
    # search studies for accession number
    queryconvert = """
    select pt.PatientID,se.SeriesInstanceUID,se.SeriesDate,se.SeriesNumber,se.SeriesDescription,se.Modality 
    from Series   se 
    join Studies  st on se.StudyInstanceUID = st.StudyInstanceUID 
    join Patients pt on st.PatientsUID      = pt.UID 
    where se.SeriesDescription like '%%%%phase%%%%' and  (%s);""" % " or  ".join(sqlStudyList )

    print "queryconvert "
    print queryconvert 
    print " "
#############################################################
# transfer data
#############################################################
elif (options.movescu ):
  tagsconn = sqlite3.connect('./pacsquery.sql')
  querymovescu =  configini.get('sql','querymovescu')
  sqlSeriesList = [ xtmp for xtmp in tagsconn.execute( querymovescu )]
  nsizeList = len(sqlSeriesList)
  #print sqlSeriesList,nsizeList 
  for idseries,(SeriesInstanceUID, StudyInstanceUID, Modality, SeriesDescription, StdOut, StdErr, ReturnCode, MoveSeriesCMD) in enumerate(sqlSeriesList):
    print idseries, nsizeList ,ReturnCode , Modality, SeriesDescription, MoveSeriesCMD,
    if ( ReturnCode == 0 ): 
       print "transfer success!!!\n"  
    else:
       print "transfering..." 
       movechild = subprocess.Popen(MoveSeriesCMD,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
       (moveout,moveerr) = movechild.communicate()
       # insert return code and output
       dhtableentry=(SeriesInstanceUID, StudyInstanceUID,  Modality, SeriesDescription ,unicode(moveout),unicode(moveerr),movechild.returncode, MoveSeriesCMD )
       print dhtableentry
       tagsconn.execute('replace into Series (SeriesInstanceUID,StudyInstanceUID,Modality,SeriesDescription,StdOut,StdErr,ReturnCode,MoveSeriesCMD) values (?,?,?,?,?,?,?,?);' , dhtableentry)
       # commit each transfer patient
       tagsconn.commit()
#############################################################
# convert to nifti
#############################################################
elif (options.convert ):
  import itk
  ImageType  = itk.Image.SS3
  slicerdb = sqlite3.connect('/Dbase/mdacc/qayyum/ctkDICOM.sql')
  ProcessDirectory = "nifti/"
  DataDirectory = "/Dbase/mdacc/qayyum/%s" % ProcessDirectory 
  queryconvert =  configini.get('sql','queryconvert')
  sqlSeriesList = [ xtmp for xtmp in slicerdb.execute(queryconvert )]
  nsizeList = len(sqlSeriesList)
  dbkey      = file('dbkey.csv' ,'w')
  dbkey.write('mrn,accessionnumber,seriesnumber,seriesdesription,seriesuid,modality,filename \n')
  fileHandle = file('segment.makefile' ,'w')
  fileHandle.write('AMIRACMD = vglrun /opt/apps/amira542/bin/start \n')
  fileHandle.write('C3DEXE = /opt/apps/itksnap/c3d-1.0.0-Linux-x86_64/bin/c3d \n')
  jobupdatelist  = []
  initialseglist = []
  for idfile,(mrn,accessionnumber,seriesnumber,seriesuid,seriesdesription,modality) in enumerate(sqlSeriesList):
    print mrn, seriesuid ,idfile,nsizeList , "Slice Thick",
    # get files and sort by location
    dicomfilelist = [ "%s" % xtmp[0] for xtmp in slicerdb.execute(" select Filename  from Images where SeriesInstanceUID  =  '%s' " % seriesuid) ]
    orderfilehelper = {}
    for seriesfile in dicomfilelist:
      dcmhelper=dicom.read_file(seriesfile);
      SliceLocation  = dcmhelper.SliceLocation
      SliceThickness = dcmhelper.SliceThickness
      print SliceThickness, 
      orderfilehelper[float(SliceLocation )] = seriesfile
    sortdicomfilelist = [ orderfilehelper[location] for location in sorted(orderfilehelper)]
    #print sortdicomfilelist 

    # nameGenerator = itk.GDCMSeriesFileNames.New()
    # nameGenerator.SetUseSeriesDetails( True ) 
    # os.walk will recursively look through directories
    # nameGenerator.RecursiveOff() 
    # nameGenerator.AddSeriesRestriction("0008|0021") 

    nameGenerator = itk.DICOMSeriesFileNames.New()
    nameGenerator.SetFileNameSortingOrderToSortBySliceLocation( ) 

    # TODO - error check unique diretory
    dicomdirectory = dicomfilelist[0].split('/')
    dicomdirectory.pop()
    seriesdirectory = "/".join(dicomdirectory)
    nameGenerator.SetDirectory( seriesdirectory   ) 
    fileNames = nameGenerator.GetFileNames( seriesuid ) 
    print seriesdirectory,fileNames 

    reader = itk.ImageSeriesReader[ImageType].New()
    dicomIO = itk.GDCMImageIO.New()
    reader.SetImageIO( dicomIO.GetPointer() )
    reader.SetFileNames( fileNames )
    reader.Update( )
    print "test",seriesuid
    # get dictionary info
    outfilename =  seriesuid.replace('.','-' ) 
    outfilename =  '%s-%s-%s' % (mrn,accessionnumber,seriesnumber)
    # outfilename = "%s/StudyDate%sSeriesNumber%s_%s_%sPatientID%s_%s" %(ProcessDirectory,StudyDate,\
    #        ''.join(e for e in SeriesNumber      if e.isalnum()),\
    #        ''.join(e for e in SeriesDescription if e.isalnum()),\
    #        ''.join(e for e in StudyDescription  if e.isalnum()),\
    #        ''.join(e for e in PatientID         if e.isalnum()),\
    #                           Modality )
    print "writing:", outfilename, seriesuid ,seriesdesription,modality
    dbkey.write('%s,%s,%s,%s,%s,%s,%s \n' %  (mrn,accessionnumber, seriesnumber,seriesdesription,seriesuid ,modality,outfilename) )
    niiwriter = itk.ImageFileWriter[ImageType].New()
    niiwriter.SetInput( reader.GetOutput() )
    #TODO set vtk array name to the series description for ID
    #vtkvectorarray.SetName(SeriesDescription)
    niiwriter.SetFileName( "nifti/%s.nii.gz" % outfilename );
    niiwriter.Update() 
    fileHandle.write('nifti/%s-label.nii.gz: nifti/%s.nii.gz\n\t echo %s; $(C3DEXE) $< -scale 0.0 -type uchar -o $@ \n' % (outfilename ,outfilename,seriesuid ))
    jobupdatelist.append ('SegmentationUpdate/%s-label.nii.gz' % outfilename) 
    initialseglist.append( 'nifti/%s-label.nii.gz' % outfilename) 
    fileHandle.write('SegmentationUpdate/%s-label.nii.Labelfield.nii: nifti/%s-label.nii.gz\n\t $(AMIRACMD) -tclcmd "load %s/%s.nii.gz ; load %s/%s-label.nii.gz; create HxCastField; CastField data connect %s-label.nii.gz; CastField outputType setIndex 0 6; CastField create setLabel; %s-label.nii.Labelfield ImageData connect %s.nii.gz" \n' % (outfilename ,outfilename ,DataDirectory ,outfilename ,DataDirectory ,outfilename ,outfilename ,outfilename ,outfilename) )
    fileHandle.write('%s-label.nii.gz: SegmentationUpdate/%s-label.nii.Labelfield.nii\n\t  $(C3DEXE) $< SegmentationUpdate/$@ ; $(AMIRACMD) -tclcmd "load %s/%s.nii.gz ; load ./SegmentationUpdate/%s-label.nii.gz; create HxCastField; CastField data connect %s-label.nii.gz; CastField outputType setIndex 0 6; CastField create setLabel; %s-label.nii.Labelfield ImageData connect %s.nii.gz" \n' % (outfilename ,outfilename ,DataDirectory ,outfilename ,outfilename ,outfilename ,outfilename ,outfilename) )
    fileHandle.flush()
    dbkey.flush()
    ## convertcmd = "dcm2nii -b /Dbase/mdacc/qayyum/dcm2nii.ini -o /Dbase/mdacc/qayyum/nifti %s " % " ".join( dicomfilelist )
    ## print convertcmd 
    ## os.system(convertcmd)
  fileHandle.close()
  dbkey.close()
  with file('segment.makefile', 'r') as original: datastream = original.read()
  with file('segment.makefile', 'w') as modified: modified.write(  'amiraupdate: %s \n' % ' '.join(jobupdatelist) + 'initial: %s \n' % ' '.join(initialseglist) + datastream)
else:
  parser.print_help()
  print options


