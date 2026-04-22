Map<String, Schema.SObjectType> gd = Schema.getGlobalDescribe();
Schema.DescribeSObjectResult d = gd.get('ExternalDataConnector').getDescribe();
System.debug('CREATEABLE=' + d.isCreateable() + ' UPDATEABLE=' + d.isUpdateable() + ' DELETABLE=' + d.isDeletable());
List<String> fieldNames = new List<String>(d.fields.getMap().keySet());
fieldNames.sort();
System.debug('FIELDS=' + JSON.serialize(fieldNames));
System.debug('ROWS=' + JSON.serialize(Database.query('SELECT Id, DeveloperName, MasterLabel FROM ExternalDataConnector LIMIT 5')));
