Schema.SObjectType t = ((Id)'1WMKZ000000GouI4AS').getSObjectType();
Schema.DescribeSObjectResult d = t.getDescribe();
System.debug('NAME=' + d.getName());
System.debug('CREATEABLE=' + d.isCreateable() + ' UPDATEABLE=' + d.isUpdateable() + ' DELETABLE=' + d.isDeletable());
List<String> fieldNames = new List<String>(d.fields.getMap().keySet());
fieldNames.sort();
System.debug('FIELDS=' + JSON.serialize(fieldNames));
System.debug('ROW=' + JSON.serialize(Database.query('SELECT Id, Name FROM ' + d.getName() + ' LIMIT 1')));
