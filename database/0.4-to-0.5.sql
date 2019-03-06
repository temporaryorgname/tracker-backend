BEGIN;

DO $$ BEGIN
IF EXISTS (select * from meta where key='SCHEMA_VERSION' AND value='0.4') THEN

----------------------------------------------------------------------------------------------------
--- Update script starts here
----------------------------------------------------------------------------------------------------

UPDATE public.meta SET value='0.5' WHERE key='SCHEMA_VERSION';

CREATE TABLE public.data_food(
	id integer PRIMARY KEY,
	name varchar(256)
);
CREATE TABLE public.data_nutrition(
	id integer PRIMARY KEY,
	food_id integer,
	creator_id integer,
	data_source varchar(256),
	location_country varchar(256),
	quantity numeric,
	quantity_units varchar(64),
	nutrition jsonb
);
COMMENT ON COLUMN public.data_nutrition.food_id is 'ID from the public.data_food table';
COMMENT ON COLUMN public.data_nutrition.data_course is 'URL or organization name';
COMMENT ON COLUMN public.data_nutrition.location_country is 'Standard nutritional values can differ by country';

CREATE TABLE public.data_food_units(
	id integer PRIMARY KEY,
	food_id integer,
	creator_id integer,
	quantity numeric,
	quantity_units varchar(64),
);

ALTER TABLE public.food ADD "premade" boolean;
COMMENT ON COLUMN public.food.premade is 'Whether or not this is food prepared ahead of time, and not actually consumed on the recorded date.';
ALTER TABLE public.food ADD "copied_from" integer;
COMMENT ON COLUMN public.food.coped_from is 'If this entry\'s data was copied from a different entry, or is premade, reference that entry here.';
ALTER TABLE public.food ADD "finished" boolean;
COMMENT ON COLUMN public.food.finished is 'Meant for premade entries. Whether the premade food was fully consumed and should be hidden from the user.';

----------------------------------------------------------------------------------------------------
--- Update script ends here
----------------------------------------------------------------------------------------------------

END IF;
END $$;
