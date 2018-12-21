BEGIN;

UPDATE public.meta SET value='0.3' WHERE key='SCHEMA_VERSION';

ALTER TABLE public.food_photos ADD time_taken timestamp;
ALTER TABLE public.food_photos ADD upload_time timestamp;
