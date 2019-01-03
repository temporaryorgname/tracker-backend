BEGIN;

UPDATE public.meta SET value='0.3' WHERE key='SCHEMA_VERSION';

ALTER TABLE public.food_photos RENAME TO photo;
ALTER TABLE public.food_photo_labels RENAME TO photo_label;
ALTER TABLE public.tags RENAME TO tag;

ALTER TABLE public.photo ADD "date" date;
ALTER TABLE public.photo ADD "time" time;
ALTER TABLE public.photo ADD upload_time timestamp;

CREATE TABLE public.photo_group (
	id serial PRIMARY KEY,
	parent_id integer REFERENCES public.photo_group(id),
	"date" date NOT NULL,
	user_id integer NOT NULL REFERENCES public.users(id)
);

ALTER TABLE public.food ADD "photo_group_id" integer REFERENCES public.photo_group(id);
ALTER TABLE public.food ADD "photo_id" integer REFERENCES public.photo(id);
ALTER TABLE public.photo ADD group_id integer REFERENCES public.photo_group(id);
UPDATE public.food
   SET photo_id = public.photo.id
   FROM public.photo
   WHERE public.food.id = public.photo.food_id;
UPDATE public.photo
   SET date = public.food.date
   FROM public.food
   WHERE public.photo.food_id = public.food.id;
ALTER TABLE public.photo DROP food_id;
