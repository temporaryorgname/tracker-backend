BEGIN;

DO $$ BEGIN
IF EXISTS (select * from meta where key='SCHEMA_VERSION' AND value='0.3') THEN

----------------------------------------------------------------------------------------------------
--- Update script starts here
----------------------------------------------------------------------------------------------------

UPDATE public.meta SET value='0.4' WHERE key='SCHEMA_VERSION';

CREATE TABLE public.user_profile (
	id integer REFERENCES public.users(id) PRIMARY KEY,
	display_name varchar(256),
	last_activity date,
	gender varchar(64),
	prefered_units varchar(32),
	target_weight numeric,
	target_calories numeric,
	weight_goal varchar(64),
	country varchar(128),
	state varchar(128),
	city varchar(128)
);
--- All users using pounds up until this point
INSERT INTO public.user_profile (id, display_name, last_activity, prefered_units) SELECT id, name, last_activity, 'lbs' FROM public.users;

ALTER TABLE public.users DROP COLUMN name;
ALTER TABLE public.users DROP COLUMN last_activity;

CREATE TABLE public.tag_relation (
	parent_id integer REFERENCES public.tag(id),
	child_id integer REFERENCES public.tag(id)
);
ALTER TABLE public.tag DROP COLUMN parent_id;

--- All bodyweight entries were saved in lbs until now
--- Convert everything to SI units
UPDATE public.body SET bodyweight=bodyweight*0.45359237;

ALTER TABLE public.food ALTER COLUMN name TYPE varchar(255);

----------------------------------------------------------------------------------------------------
--- Update script ends here
----------------------------------------------------------------------------------------------------

END IF;
END $$;

