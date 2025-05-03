create table public.avg_industrial_prices (
  subzone text not null,
  sub_category text not null,
  listing_type text not null,
  average_price numeric(12, 2) not null,
  constraint avg_industrial_prices_pkey primary key (subzone, sub_category, listing_type)
) TABLESPACE pg_default;