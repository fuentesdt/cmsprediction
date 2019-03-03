
# build data base from CSV file
def GetDataDictionary():
  import csv
  CSVDictionary = {}
  with open('datalocation/cmsdata.csv', 'r') as csvfile:
    myreader = csv.DictReader(csvfile, delimiter='\t')
    for row in myreader:
       CSVDictionary[int( row['MRN'])]  =  row
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
DROP TABLE IF EXISTS 'lstat' ;
DROP TABLE IF EXISTS 'overlap' ;

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

CREATE TABLE lstat  (
   InstanceUID        VARCHAR(255)  NOT NULL,  --  'studyuid *OR* seriesUID'
   SegmentationID     VARCHAR(80)   NOT NULL,  -- UID for segmentation file 
   FeatureID          VARCHAR(80)   NOT NULL,  -- UID for image feature     
   LabelID            INT           NOT NULL,  -- label id for LabelSOPUID statistics of FeatureSOPUID
   Mean               REAL              NULL,
   StdD               REAL              NULL,
   Max                REAL              NULL,
   Min                REAL              NULL,
   Count              INT               NULL,
   Volume             REAL              NULL,
   ExtentX            INT               NULL,
   ExtentY            INT               NULL,
   ExtentZ            INT               NULL,
   PRIMARY KEY (InstanceUID,SegmentationID,FeatureID,LabelID) );


CREATE TABLE overlap(
   compid             int           NOT NULL,  --   c3d -comp Component ID 
   InstanceUID        VARCHAR(255)  NOT NULL,  --  'studyuid *OR* seriesUID',  
   FirstImage         VARCHAR(80)   NOT NULL,  -- UID for  FirstImage  
   SecondImage        VARCHAR(80)   NOT NULL,  -- UID for  SecondImage 
   LabelID            INT           NOT NULL,  -- label id for LabelSOPUID statistics of FeatureSOPUID 
   SegmentationID     VARCHAR(80)   NOT NULL,  -- UID for segmentation file  to join with lstat
   -- output of c3d firstimage.nii.gz secondimage.nii.gz -overlap LabelID
   -- Computing overlap #1 and #2
   -- OVL: 6, 11703, 7362, 4648, 0.487595, 0.322397  
   MatchingFirst      int           DEFAULT NULL,     --   Matching voxels in first image:  11703
   MatchingSecond     int           DEFAULT NULL,     --   Matching voxels in second image: 7362
   SizeOverlap        int           DEFAULT NULL,     --   Size of overlap region:          4648
   DiceSimilarity     real          DEFAULT NULL,     --   Dice similarity coefficient:     0.487595
   IntersectionRatio  real          DEFAULT NULL,     --   Intersection / ratio:            0.322397
   PRIMARY KEY (compid,InstanceUID,FirstImage,SecondImage,LabelID,SegmentationID) );
"""



from optparse import OptionParser
parser = OptionParser()
parser.add_option( "--initialize",
                  action="store_true", dest="initialize", default=False,
                  help="build initial sql file ", metavar = "BOOL")
parser.add_option( "--dbfile",
                  action="store", dest="dbfile", default="datalocation/cmsdata.csv",
                  help="training data file", metavar="string")
parser.add_option( "--querydb",
                  action="store_true", dest="querydb", default=False,
                  help="build query commands ", metavar = "BOOL")
parser.add_option( "--convert",
                  action="store_true", dest="convert", default=False,
                  help="convert dicom to nifti", metavar = "BOOL")
parser.add_option( "--builddb",
                  action="store_true", dest="builddb", default=False,
                  help="build deps", metavar = "BOOL")

(options, args) = parser.parse_args()
#############################################################
# build initial sql file 
#############################################################
if (options.initialize ):
  import sqlite3
  import pandas
  import os
  #import time
  #import dicom
  #import subprocess,re,os
  #import ConfigParser

  # deprecated 
  #databaseinfo = GetDataDictionary()

  # build new database
  os.system('rm datalocation/databaseinfo.sqlite')
  tagsconn = sqlite3.connect('datalocation/databaseinfo.sqlite')
  for sqlcmd in initializedb.split(";"):
     tagsconn.execute(sqlcmd )
  # load csv file
  df = pandas.read_csv(options.dbfile,delimiter='\t')
  df.to_sql('cmsdata', tagsconn , if_exists='append', index=False)
#############################################################
# build db
#############################################################
elif (options.builddb ):
  import sqlite3
  tagsconn = sqlite3.connect('datalocation/databaseinfo.sqlite')
  cursor = tagsconn.execute(' SELECT aq.MRN,aq.StudyDate,aq.StudyUID,aq.SeriesUID, printf("%s/%s/%s/%s", aq.MRN,REPLACE(aq.StudyDate, "-", ""),aq.StudyUID,aq.SeriesUID) UID, aq.SOP, 91.234 AcquisitionTime FROM cmsdata aq where aq.StudyUID is not NULL;' )
  names = [description[0] for description in cursor.description]
  sqlStudyList = [ dict(zip(names,xtmp)) for xtmp in cursor ]

  # build makefile deps
  with open('datalocation/dependencies'  ,'w') as fileHandle:
      fileHandle.write('UIDLIST = %s \n' % " ".join([ data['UID'] for data in sqlStudyList ]))
      for data in sqlStudyList:
         fileHandle.write("ImageDatabase/%s/Ven.raw.nii.gz: ImageDatabase/%s/raw.xfer: \n\tif [ ! -f ImageDatabase/%s/%s.nii.gz   ] ; then mkdir -p ImageDatabase/%s ;$(DCMNIFTISPLIT) $(subst ImageDatabase,/FUS4/IPVL_research,$(<D)) $(@D)  \'0008|0032\' ; else echo skipping network filesystem; fi\n\tln -snf ./%s/%s.nii.gz $@; touch -h -r $(@D)/%s/%s.nii.gz  $@;\n\tln -snf ./%s/ $(subst .nii.gz,.dir,$@)')\n" % (data['UID'],data['UID'],data['UID'],data['AcquisitionTime'],data['UID'],data['seriesUID'],data['AcquisitionTime'],data['seriesUID'],data['AcquisitionTime'],data['seriesUID']) )

      
      


# SELECT concat_WS('/','/FUS4/IPVL_research',aq.MRN,REPLACE(aq.StudyDate, '-', ''),aq.StudyUID,aq.SeriesUID) dcmpath, aq.SOP FROM cmsdata aq



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
      print ("\n study",iddata,nsize,StudyReturnCode,FindStudiesCMD, study)
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
          print("more than one entry ? studyUID should be unique? ", sqlStudyList )
          raise RuntimeError
        for series  in seriesdictionary:
          print(series )
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
              print("more than one entry ? seriesUID should be unique? ", seriesuid )
              raise RuntimeError
          #except KeyError as inst:
          else:
            print("error reading: ", series  ,seriesdictionary)
            raise RuntimeError
      else:
        print("?? error reading: study ",study)
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
    print( "querymovescu "  )
    print( querymovescu     )
    print( " "              )
    # search studies for accession number
    queryconvert = """
    select pt.PatientID,se.SeriesInstanceUID,se.SeriesDate,se.SeriesNumber,se.SeriesDescription,se.Modality 
    from Series   se 
    join Studies  st on se.StudyInstanceUID = st.StudyInstanceUID 
    join Patients pt on st.PatientsUID      = pt.UID 
    where se.SeriesDescription like '%%%%phase%%%%' and  (%s);""" % " or  ".join(sqlStudyList )

    print( "queryconvert " )
    print( queryconvert    )
    print( " "             )
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
    print(mrn, seriesuid ,idfile,nsizeList , "Slice Thick",)
    # get files and sort by location
    dicomfilelist = [ "%s" % xtmp[0] for xtmp in slicerdb.execute(" select Filename  from Images where SeriesInstanceUID  =  '%s' " % seriesuid) ]
    orderfilehelper = {}
    for seriesfile in dicomfilelist:
      dcmhelper=dicom.read_file(seriesfile);
      SliceLocation  = dcmhelper.SliceLocation
      SliceThickness = dcmhelper.SliceThickness
      print(SliceThickness, )
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
    print(seriesdirectory,fileNames )

    reader = itk.ImageSeriesReader[ImageType].New()
    dicomIO = itk.GDCMImageIO.New()
    reader.SetImageIO( dicomIO.GetPointer() )
    reader.SetFileNames( fileNames )
    reader.Update( )
    print("test",seriesuid)
    # get dictionary info
    outfilename =  seriesuid.replace('.','-' ) 
    outfilename =  '%s-%s-%s' % (mrn,accessionnumber,seriesnumber)
    # outfilename = "%s/StudyDate%sSeriesNumber%s_%s_%sPatientID%s_%s" %(ProcessDirectory,StudyDate,\
    #        ''.join(e for e in SeriesNumber      if e.isalnum()),\
    #        ''.join(e for e in SeriesDescription if e.isalnum()),\
    #        ''.join(e for e in StudyDescription  if e.isalnum()),\
    #        ''.join(e for e in PatientID         if e.isalnum()),\
    #                           Modality )
    print("writing:", outfilename, seriesuid ,seriesdesription,modality)
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
  print (options)


