BEGIN;

DO $$ BEGIN
IF EXISTS (select * from meta where key='SCHEMA_VERSION' AND value='0.4') THEN

----------------------------------------------------------------------------------------------------
--- Update script starts here
----------------------------------------------------------------------------------------------------

UPDATE public.meta SET value='0.5' WHERE key='SCHEMA_VERSION';

ALTER TABLE public.photo ADD "food_id" integer;
UPDATE public.photo p SET food_id=(SELECT id FROM public.food WHERE photo_id=p.id OR (photo_group_id=p.group_id AND parent_id IS NULL));

-- TODO on next iteration. Can't delete them on the same transaction block as the stuff above.
--ALTER TABLE public.food DROP COLUMN photo_id;
--ALTER TABLE public.food DROP COLUMN photo_group_id;
--ALTER TABLE public.photo DROP COLUMN group_id;

----------------------------------------------------------------------------------------------------
--- Update script ends here
----------------------------------------------------------------------------------------------------

END IF;
END $$;

