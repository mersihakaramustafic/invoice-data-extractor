-- Enable required extensions (already available in Supabase by default)
create extension if not exists pg_cron;
create extension if not exists pg_net;

-- Schedule invoice processing every hour at :00
select cron.schedule(
  'process-invoices',
  '0 * * * *',
  $$
    select net.http_post(
      url     := 'https://invoice-data-extractor-xi.vercel.app/invoices/batch',
      headers := '{"Content-Type": "application/json"}'::jsonb,
      body    := '{}'::jsonb
    );
  $$
);

-- View all scheduled jobs
-- select * from cron.job;

-- Remove the job
-- select cron.unschedule('process-invoices');
