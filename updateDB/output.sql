set nocount on
declare @xmls nvarchar(max)

print ('Syncing GiroDeductionFile (549 of 1491)')
   set @xmls = cast('' as nvarchar(max)) + 
      '<sch><nm>BatchID</nm><d>nvarchar(5)</d><t>nvarchar</t><s>5</s><p>0</p><l>0</l><n>Y</n><pk>N</pk><part></part></sch>' + 
      '<sch><nm>BatchNumber</nm><d>int</d><t>int</t><s>4</s><p>0</p><l>0</l><n>Y</n><pk>N</pk><part></part></sch>' + 
      '<sch><nm>BusinessUnitID</nm><d>uniqueidentifier</d><t>uniqueidentifier</t><s>16</s><p>0</p><l>0</l><n>Y</n><pk>N</pk><part></part></sch>' + 
      '<sch><nm>CompanyID</nm><d>nvarchar(12)</d><t>nvarchar</t><s>12</s><p>0</p><l>0</l><n>Y</n><pk>N</pk><part></part></sch>' + 
      '<sch><nm>CreatedDateTime</nm><d>datetime2</d><t>datetime2</t><s>8</s><p>0</p><l>0</l><n>Y</n><pk>N</pk><part></part></sch>' + 
      '<sch><nm>CreatedID</nm><d>uniqueidentifier</d><t>uniqueidentifier</t><s>16</s><p>0</p><l>0</l><n>Y</n><pk>N</pk><part></part></sch>' + 
      '<sch><nm>DeductionFileName</nm><d>nvarchar(255)</d><t>nvarchar</t><s>255</s><p>0</p><l>0</l><n>Y</n><pk>N</pk><part></part></sch>' + 
      '<sch><nm>GenerationDate</nm><d>datetime2</d><t>datetime2</t><s>8</s><p>0</p><l>0</l><n>Y</n><pk>N</pk><part></part></sch>' + 
      '<sch><nm>GiroAdhocDeductionID</nm><d>uniqueidentifier</d><t>uniqueidentifier</t><s>16</s><p>0</p><l>0</l><n>Y</n><pk>N</pk><part></part></sch>' + 
      '<sch><nm>GiroDeductionEncryptedFileByteID</nm><d>uniqueidentifier</d><t>uniqueidentifier</t><s>16</s><p>0</p><l>0</l><n>Y</n><pk>N</pk><part></part></sch>' + 
      '<sch><nm>GiroDeductionFileByteID</nm><d>uniqueidentifier</d><t>uniqueidentifier</t><s>16</s><p>0</p><l>0</l><n>Y</n><pk>N</pk><part></part></sch>' + 
      '<sch><nm>GiroDeductionID</nm><d>uniqueidentifier</d><t>uniqueidentifier</t><s>16</s><p>0</p><l>0</l><n>Y</n><pk>N</pk><part></part></sch>' + 
      '<sch><nm>HashValue</nm><d>nvarchar(50)</d><t>nvarchar</t><s>50</s><p>0</p><l>0</l><n>Y</n><pk>N</pk><part></part></sch>' + 
      '<sch><nm>IsDeleted</nm><d>bit</d><t>bit</t><s>1</s><p>0</p><l>0</l><n>Y</n><pk>N</pk><part></part></sch>' + 
      '<sch><nm>IsInterfaceFileSuccessfullyUploaded</nm><d>int</d><t>int</t><s>4</s><p>0</p><l>0</l><n>Y</n><pk>N</pk><part></part></sch>' + 
      '<sch><nm>IsItemsStatusFullyUpdated</nm><d>bit</d><t>bit</t><s>1</s><p>0</p><l>0</l><n>Y</n><pk>N</pk><part></part></sch>' + 
      '<sch><nm>KyribaExportHistoryID</nm><d>uniqueidentifier</d><t>uniqueidentifier</t><s>16</s><p>0</p><l>0</l><n>Y</n><pk>N</pk><part></part></sch>' + 
      '<sch><nm>KyribaFileGenerationIndicator</nm><d>bit</d><t>bit</t><s>1</s><p>0</p><l>0</l><n>Y</n><pk>N</pk><part></part></sch>' + 
      '<sch><nm>LastNotifiedDateTimeForGIRODeductionFileFailedToUpload</nm><d>datetime2</d><t>datetime2</t><s>8</s><p>0</p><l>0</l><n>Y</n><pk>N</pk><part></part></sch>' + 
      '<sch><nm>LastNotifiedDateTimeForGIRODeductionFileMissingReturnFile</nm><d>datetime2</d><t>datetime2</t><s>8</s><p>0</p><l>0</l><n>Y</n><pk>N</pk><part></part></sch>' + 
      '<sch><nm>ModifiedDateTime</nm><d>datetime2</d><t>datetime2</t><s>8</s><p>0</p><l>0</l><n>Y</n><pk>N</pk><part></part></sch>' + 
      '<sch><nm>ModifiedUser</nm><d>nvarchar(50)</d><t>nvarchar</t><s>50</s><p>0</p><l>0</l><n>Y</n><pk>N</pk><part></part></sch>' + 
      '<sch><nm>ObjectID</nm><d>uniqueidentifier</d><t>uniqueidentifier</t><s>16</s><p>0</p><l>0</l><n>N</n><pk>Y</pk><part></part></sch>' + 
      '<sch><nm>ObjectNumber</nm><d>nvarchar(200)</d><t>nvarchar</t><s>200</s><p>0</p><l>0</l><n>Y</n><pk>N</pk><part></part></sch>' + 
      '<sch><nm>ORGBankACCName</nm><d>nvarchar(140)</d><t>nvarchar</t><s>140</s><p>0</p><l>0</l><n>Y</n><pk>N</pk><part></part></sch>' + 
      '<sch><nm>ORGBankACCNo</nm><d>nvarchar(34)</d><t>nvarchar</t><s>34</s><p>0</p><l>0</l><n>Y</n><pk>N</pk><part></part></sch>' + 
      '<sch><nm>ORGBankCode</nm><d>nvarchar(50)</d><t>nvarchar</t><s>50</s><p>0</p><l>0</l><n>Y</n><pk>N</pk><part></part></sch>' + 
      '<sch><nm>ORGBankName</nm><d>nvarchar(50)</d><t>nvarchar</t><s>50</s><p>0</p><l>0</l><n>Y</n><pk>N</pk><part></part></sch>' + 
      '<sch><nm>ORGBankSwiftCode</nm><d>nvarchar(11)</d><t>nvarchar</t><s>11</s><p>0</p><l>0</l><n>Y</n><pk>N</pk><part></part></sch>' + 
      '<sch><nm>ORGTransactionCode</nm><d>nvarchar(50)</d><t>nvarchar</t><s>50</s><p>0</p><l>0</l><n>Y</n><pk>N</pk><part></part></sch>' + 
      '<sch><nm>TotalAmountOfAccepted</nm><d>decimal(19,4)</d><t>decimal</t><s>19</s><p>19</p><l>4</l><n>Y</n><pk>N</pk><part></part></sch>' + 
      '<sch><nm>TotalAmountOfReconciled</nm><d>decimal(19,4)</d><t>decimal</t><s>19</s><p>19</p><l>4</l><n>Y</n><pk>N</pk><part></part></sch>' + 
      '<sch><nm>TotalAmountOfRejected</nm><d>decimal(19,4)</d><t>decimal</t><s>19</s><p>19</p><l>4</l><n>Y</n><pk>N</pk><part></part></sch>' + 
      '<sch><nm>TotalAmountOfTransaction</nm><d>decimal(19,4)</d><t>decimal</t><s>19</s><p>19</p><l>4</l><n>Y</n><pk>N</pk><part></part></sch>' + 
      '<sch><nm>TotalNumberOfAccepted</nm><d>int</d><t>int</t><s>4</s><p>0</p><l>0</l><n>Y</n><pk>N</pk><part></part></sch>' + 
      '<sch><nm>TotalNumberOfReconciled</nm><d>int</d><t>int</t><s>4</s><p>0</p><l>0</l><n>Y</n><pk>N</pk><part></part></sch>' + 
      '<sch><nm>TotalNumberOfRejected</nm><d>int</d><t>int</t><s>4</s><p>0</p><l>0</l><n>Y</n><pk>N</pk><part></part></sch>' + 
      '<sch><nm>TotalNumberOfTransaction</nm><d>int</d><t>int</t><s>4</s><p>0</p><l>0</l><n>Y</n><pk>N</pk><part></part></sch>' + 
      '<sch><nm>VersionNumber</nm><d>int</d><t>int</t><s>4</s><p>0</p><l>0</l><n>Y</n><pk>N</pk><part></part></sch>' + 
   '';
   exec sp_schemasynctableandcolumns 'GiroDeductionFile', @xmls
print ('    Table: GiroDeductionFile synchronized')

set nocount off
