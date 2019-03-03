SELECT * FROM
(

SELECT  uploadID,

JSON_UNQUOTE(data->"$.""Number""") "Number",

JSON_UNQUOTE(data->"$.""Patient""") "Patient",

JSON_UNQUOTE(data->"$.""MRN""") "MRN",

JSON_UNQUOTE(data->"$.""Physician""") "Physician",

JSON_UNQUOTE(data->"$.""Date of Request""") "Date of Request",

JSON_UNQUOTE(data->"$.""Results""") "Results",

JSON_UNQUOTE(data->"$.""CMS detail""") "CMS detail",

JSON_UNQUOTE(data->"$.""comments""") "comments",

JSON_UNQUOTE(data->"$.""KRAS (1=Y; N=0)""") "KRAS (1=Y; N=0)",

JSON_UNQUOTE(data->"$.""Age""") "Age",

JSON_UNQUOTE(data->"$.""Sex""") "Sex",

JSON_UNQUOTE(data->"$.""Race""") "Race",

JSON_UNQUOTE(data->"$.""Image Date""") "Image Date",

JSON_UNQUOTE(data->"$.""Im. Accession No.""") "Im. Accession No.",

JSON_UNQUOTE(data->"$.""UID""") "UID",

JSON_UNQUOTE(data->"$.""Series""") "Series",

JSON_UNQUOTE(data->"$.""images""") "images",

#JSON_UNQUOTE(data->"$.""comments""") "comments",

JSON_UNQUOTE(data->"$.""AQ""") "AQ",

JSON_UNQUOTE(data->"$.""primary location: R =1; L = 2""") "primary location: R =1; L = 2",

JSON_UNQUOTE(data->"$.""no. mets (pv) """) "no. mets (pv) ",

JSON_UNQUOTE(data->"$.""no. mets (pv) <3 = 1; 3-5= 2; 6-10 =3; >10 = 4""") "no. mets (pv) <3 = 1; 3-5= 2; 6-10 =3; >10 = 4",

JSON_UNQUOTE(data->"$.""largest met size (cm)""") "largest met size (cm)",

JSON_UNQUOTE(data->"$.""Ca++ N= 0; Y = 2""") "Ca++ N= 0; Y = 2",

JSON_UNQUOTE(data->"$.""Tv (met enh portal venous phase)""") "Tv (met enh portal venous phase)",

JSON_UNQUOTE(data->"$.""Tv SD""") "Tv SD",

JSON_UNQUOTE(data->"$.""Liv_v (background liver - venous)""") "Liv_v (background liver - venous)",

JSON_UNQUOTE(data->"$.""Liv_v SD""") "Liv_v SD",

JSON_UNQUOTE(data->"$.""Aov (aorta portal venous phase)""") "Aov (aorta portal venous phase)",

JSON_UNQUOTE(data->"$.""Aov_SD""") "Aov_SD",

JSON_UNQUOTE(data->"$.""Tv/Aov""") "Tv/Aov",

JSON_UNQUOTE(data->"$.""margin (axial & coronal): smooth =1; microblob=2; macrolob 3""") "margin (axial & coronal): smooth =1; microblob=2; macrolob 3",

JSON_UNQUOTE(data->"$.""central hetero enhan Y=1; N=0 (>75%)""") "central hetero enhan Y=1; N=0 (>75%)",

JSON_UNQUOTE(data->"$.""necrosis N=0 Y=1""") "necrosis N=0 Y=1",

JSON_UNQUOTE(data->"$.""Adj liver enh (Y=1; N=0)""") "Adj liver enh (Y=1; N=0)",

JSON_UNQUOTE(data->"$.""capsule retraction (1=Y; 0=N)""") "capsule retraction (1=Y; 0=N)",

JSON_UNQUOTE(data->"$.""CEA (ng/ml); [N is </=3.8]""") "CEA (ng/ml); [N is </=3.8]",

JSON_UNQUOTE(data->"$.""Death date""") "Death date",

JSON_UNQUOTE(data->"$.""Date of recurrence""") "Date of recurrence"

FROM ClinicalStudies.excelUpload

where uploadID = 112

) e

LEFT JOIN student_intern.aq_CMS_sop qa on e.Number = qa.id;

-- mysql < exceljoin.sql    | sed "s/\t/,/g;s/NULL//g" > datalocation/cmsdata.csv
-- mysql < exceljoin.sql    > datalocation/cmsdata.csv
