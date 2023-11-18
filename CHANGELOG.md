## November 17, 2023

### Backend

* Add POST, PUT, DELETE to Malaria and Country resources ([@kystanleylin](https://github.com/kystanleylin))
* Fix bug in import_malaria_csv(), so the primary key works properly ([@kystanleylin](https://github.com/kystanleylin))
* Fix bug to return null if no corresponding Country to a Malaria entry ([@kystanleylin](https://github.com/kystanleylin))

## November 16, 2023

### Backend

* Split DbQuery into Malaria and SiteMgmt repos ([@kystanleylin](https://github.com/kystanleylin))
* Add PUT and DELETE to Feedback and Action ([@kystanleylin](https://github.com/kystanleylin))
* Add GET by id to Feedback and Action ([@kystanleylin](https://github.com/kystanleylin))
* Change bind_key for sitemgmt.db ([@kystanleylin](https://github.com/kystanleylin))
* Add api/reset to the databases ([@kystanleylin](https://github.com/kystanleylin))

## November 15, 2023

### Backend

* Add Country table, ingested from REST Countries API ([@kystanleylin](https://github.com/kystanleylin))
* Add WHO country metadata from DataPrep ([@kystanleylin](https://github.com/kystanleylin))
* GET Malaria contains Country info ([@kystanleylin](https://github.com/kystanleylin))
* Enable multi-args (separated by comma) in malaria/filter ([@kystanleylin](https://github.com/kystanleylin))

## November 11, 2023

### Backend

* Add malaria/filter and pagination ([@Mzisbrod](https://github.com/Mzisbrod))
* Add error checking for 400 Bad Request ([@kystanleylin](https://github.com/kystanleylin))
* Add PUT and DELETE to admin resource ([@kystanleylin](https://github.com/kystanleylin))
* Use arguments in the URL ([@kystanleylin](https://github.com/kystanleylin))
* Add admin/get_action ([@kystanleylin](https://github.com/kystanleylin))

## November 7, 2023

### Backend

* Add initial set of APIs and databases ([@kystanleylin](https://github.com/kystanleylin))