BEGIN;

UPDATE public.meta SET value='0.3' WHERE key='SCHEMA_VERSION';

ALTER TABLE public.food_photos ADD "date" date;
ALTER TABLE public.food_photos ADD "time" time;
ALTER TABLE public.food_photos ADD upload_time timestamp;

CREATE TABLE public.photo_group (
	id serial PRIMARY KEY,
	parent_id integer REFERENCES public.photo_group(id),
	"date" date NOT NULL,
	user_id integer NOT NULL REFERENCES public.users(id)
);

ALTER TABLE public.food ADD "photo_group_id" integer REFERENCES public.photo_group(id);
ALTER TABLE public.food ADD "photo_id" integer REFERENCES public.food_photos(id);
ALTER TABLE public.food_photos ADD group_id integer REFERENCES public.photo_group(id);
UPDATE public.food
   SET photo_id = public.food_photos.id
   FROM public.food_photos
   WHERE public.food.id = public.food_photos.food_id;
UPDATE public.food_photos
   SET date = public.food.date
   FROM public.food
   WHERE public.food_photos.food_id = public.food.id;
ALTER TABLE public.food_photos DROP food_id;
