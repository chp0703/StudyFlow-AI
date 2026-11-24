-- Free time is no longer declared by users: planning uses an implicit 06:00-22:00 day and only busy intervals constrain it.
-- Removes the availability routine and the stored availability windows. Irreversible on real data.

-- Plans built on the removed windows may no longer be valid, so bump the revision of every affected owner:
-- older proposals then fail the existing stale-revision check instead of being approved against vanished data.
update app_private.user_profiles u
   set schedule_revision = schedule_revision + 1
 where exists (select 1 from app_private.time_windows w where w.user_id = u.user_id and w.kind = 'AVAILABILITY');

delete from app_private.time_windows where kind = 'AVAILABILITY';

drop function if exists app_api.set_availability(jsonb);
