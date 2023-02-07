BEGIN TRANSACTION;
INSERT INTO "calculator_key_value" ("id","key_name","amount","notes","equation","abrv") VALUES (1,'Harvesting Rate','113','can vary wildly depending on kind of flower being harvested (Lilies being one of the fastest to harvest)','Stems/Hhr','harvesting_rt'),
 (2,'Stem Cleaning Rate ','120','this is concerning stems that we havent harvested ourselves.','stems/Hhr','stm_cln_rt'),
 (3,'Bucket Washing Rate','50','estimated amount based on experience needs data collected.','buckets/Hhr','bkt_washing_rt'),
 (4,'Bouquet Making rate','4.5','This is from stems to wrapped bouquets. It''s also teens rate of doing things.','Bouquets/Hhr','bqt_making_rt'),
 (5,'Spray Making rate','1.5','Based on Hannah''s estimation','Sprays/Hhr','spr_making_rt'),
 (6,'Average stem use in Bouquets','25','collected average based on 2021 summer CSA''s','stems/bouquet','avg_stm_use_bqt'),
 (7,'estimated stems in sprays','70','Based on Hannah''s estimated stem us in sprays','stems/spray','est_stm_in_spr'),
 (8,'Tall bucket Stem #','120','based on experience taken with all different kinds of flowers','stems','tall_bkt_stm'),
 (9,'short bucket Bouquet #','2','based on experience of the size of our bouquets','bouquets','srt_bkt_bqt'),
 (10,'Tall bucket volume','1.723668981','calculated given the dimensions of bucket and extra of the stems','ft^3','tall_bkt_vol'),
 (11,'Short bucket volume','1.108072917','calculated given the dimensions of bucket and extra of the bouquets','ft^3','srt_bkt_vol'),
 (12,'Spray Volume','14.17824074','based on cursory internet search','ft^3','spray_vol'),
 (13,'cooler volume','706',NULL,'ft^3','cooler_vol'),
 (14,'Storage utilization rate','0.55','This is how much of the cooler can be used for storage instead of walking space','ft^3/ft^3','strg_utl_rt'),
 (15,'Optimal B Cold Storage','500 (Bouquet)','max bouquets in cold storage at any one time. assumption is that only bouquets in cooler','(Cooler Volume)*(storage utilization)*(# of B''s in bucket)/(Bucket volume)','optml_b_cold_strg'),
 (16,'Optimal stem cold storage','20,000 (Stems)','max stems in cold storage at any one time. assumption is that only stems in cooler','(Cooler Volume)*(storage utilization)*(# of stems''s in bucket)/(Bucket volume)','optml_stm_cold_strg'),
 (17,'theoretical production floor table capacity','20-30','This will limit the amount of workers we can have on the production floor in a given moment. The amount of workers depends on th our production method as well. Our two different methods could fit 1 or 3 workers per table.','(Area of production floor)*(Walking space factor)/(Table area)','thr_prod_flr_tbl_cap'),
 (18,'Max worker capacity for making','15-65','based on amount of tables and making method.','(Table capacity)*3/4 to (table capacity)*3*3/4','max_wrkr_cap_for_making');
INSERT INTO "floral_arrangments" ("id","name","stem_use","abrv") VALUES (1,'Bouquets',6,'bqt'),
 (2,'Center Pieces',6,'cps'),
 (3,'Sprays',7,'sprs');
COMMIT;
