-- SeyeGarage : migration 002, suite de la première relecture (REVUE.md, points 1 à 7)
--   1. rôles `app` et `service`, sans droit de contourner la RLS
--   2. table `utilisateurs` et clés étrangères
--   3. suppression douce des dossiers + journal des actions
--   4. numérotation automatique des dossiers (par entreprise et par année, modifiable)
--   5. quantités décimales
--   6. table `tarifs`
--   7. table `rappels`
-- À appliquer avec le rôle propriétaire. Aucun mot de passe ici : voir db/LISEZ-MOI.md.

begin;

-- ============ Suivi des migrations ============
create table public.migrations (
  nom text primary key,
  appliquee_le timestamptz not null default now()
);
insert into public.migrations (nom, appliquee_le) values ('001_schema', '2026-11-11');
insert into public.migrations (nom) values ('002_durcissement');

-- ============ 1. Rôles de connexion ============
-- `app`     : le site. Soumis à la RLS, ne possède aucune table.
-- `service` : tâches du serveur (confirmation PayDunya, rappels). Aucun accès aux données de travail.
-- Créés sans mot de passe : ils ne peuvent pas se connecter tant qu'il n'a pas été fixé hors dépôt.
do $$
declare r text;
begin
  foreach r in array array['app', 'service'] loop
    if not exists (select 1 from pg_roles where rolname = r) then
      execute format('create role %I', r);
    end if;
    execute format('alter role %I login noinherit nobypassrls nocreatedb nocreaterole', r);
  end loop;
  -- un rôle créé depuis la console Neon appartient à un groupe qui contourne la RLS : on refuse
  if exists (select 1 from pg_auth_members am join pg_roles r on r.oid = am.member
             where r.rolname in ('app', 'service')) then
    raise exception 'Les rôles app et service ne doivent appartenir à aucun autre rôle';
  end if;
end $$;

-- Par défaut PostgreSQL laisse tout le monde exécuter les fonctions : on ferme, puis on ouvre au cas par cas.
alter default privileges revoke execute on functions from public;
revoke execute on function public.app_uid(), public.est_membre(uuid), public.abonnement_actif(uuid),
  public.peut_ecrire(uuid), public.apres_creation_entreprise(), public.activer_abonnement(text) from public;

-- ============ 2. Utilisateurs ============
create table public.utilisateurs (
  id uuid primary key default gen_random_uuid(),
  email text not null unique
    check (email = lower(btrim(email)) and email ~ '^[^@[:space:]]+@[^@[:space:]]+$'),
  cree_le timestamptz not null default now()
);
alter table public.utilisateurs enable row level security;
create policy uti_select on public.utilisateurs for select using (id = public.app_uid());

alter table public.membres
  add constraint membres_user_id_fkey foreign key (user_id) references public.utilisateurs on delete cascade;
alter table public.entreprises
  add constraint entreprises_cree_par_fkey foreign key (cree_par) references public.utilisateurs;

-- Trouve le compte lié à un email, ou le crée. À appeler par le site une fois le code de connexion vérifié.
create function public.utilisateur_par_email(p_email text) returns uuid
language plpgsql security definer set search_path = public as $$
declare e text := lower(btrim(p_email)); u uuid;
begin
  insert into public.utilisateurs (email) values (e) on conflict (email) do nothing;
  select id into u from public.utilisateurs where email = e;
  return u;
end $$;

-- ============ 5. Quantités décimales (1,5 m ; 0,5 L) ============
-- La vue dépend de la colonne : on la retire, puis on la recrée plus bas.
drop view public.dossier_totaux;
alter table public.lignes alter column qte type numeric(10,2);

-- ============ Une ligne ou un versement appartient à la même entreprise que son dossier ============
alter table public.dossiers add constraint dossiers_id_entreprise_key unique (id, entreprise_id);
alter table public.clients  add constraint clients_id_entreprise_key  unique (id, entreprise_id);

alter table public.lignes drop constraint lignes_dossier_id_fkey;
alter table public.lignes add constraint lignes_dossier_fkey
  foreign key (dossier_id, entreprise_id) references public.dossiers (id, entreprise_id) on delete cascade;

alter table public.versements drop constraint versements_dossier_id_fkey;
alter table public.versements add constraint versements_dossier_fkey
  foreign key (dossier_id, entreprise_id) references public.dossiers (id, entreprise_id) on delete cascade;

alter table public.dossiers drop constraint dossiers_client_id_fkey;
alter table public.dossiers add constraint dossiers_client_fkey
  foreign key (client_id, entreprise_id) references public.clients (id, entreprise_id) on delete set null (client_id);

-- ============ 3. Suppression douce des dossiers ============
-- Un dossier ne s'efface plus : il part à la corbeille (supprime_le rempli) et peut être rétabli.
alter table public.dossiers
  add column supprime_le timestamptz,
  add column supprime_par uuid references public.utilisateurs;

-- Le numéro d'un dossier à la corbeille redevient disponible.
alter table public.dossiers drop constraint dossiers_entreprise_id_numero_key;
create unique index dossiers_numero_actif_key on public.dossiers (entreprise_id, numero) where supprime_le is null;

drop policy dossiers_delete on public.dossiers;

create function public.marquer_suppression() returns trigger
language plpgsql as $$
begin
  if new.supprime_le is not null and old.supprime_le is null then
    new.supprime_le := now();
    new.supprime_par := public.app_uid();
  elsif new.supprime_le is null then
    new.supprime_par := null;
  else
    new.supprime_le := old.supprime_le;
    new.supprime_par := old.supprime_par;
  end if;
  return new;
end $$;
create trigger trg_marquer_suppression before update on public.dossiers
  for each row execute function public.marquer_suppression();

-- ============ 3 bis. Journal des actions ============
-- Garde l'état d'avant chaque modification ou suppression, pour rétablir ou comprendre un litige.
create table public.journal (
  id bigint generated always as identity primary key,
  entreprise_id uuid not null references public.entreprises on delete cascade,
  user_id uuid references public.utilisateurs on delete set null,
  table_nom text not null,
  ligne_id uuid not null,
  action text not null check (action in ('creation','modification','suppression','corbeille','restauration')),
  avant jsonb,
  cree_le timestamptz not null default now()
);
create index on public.journal (entreprise_id, cree_le desc);
create index on public.journal (table_nom, ligne_id);
alter table public.journal enable row level security;
create policy jou_select on public.journal for select using (public.est_membre(entreprise_id));

create function public.journaliser() returns trigger
language plpgsql security definer set search_path = public as $$
declare ancien jsonb; nouveau jsonb; eid uuid; act text;
begin
  if tg_op <> 'INSERT' then ancien := to_jsonb(old); end if;
  if tg_op <> 'DELETE' then nouveau := to_jsonb(new); end if;
  if ancien = nouveau then return null; end if;
  eid := coalesce(nouveau, ancien) ->> 'entreprise_id';
  -- entreprise en cours de suppression : son journal part avec elle
  if not exists (select 1 from public.entreprises where id = eid) then return null; end if;
  act := case tg_op when 'INSERT' then 'creation' when 'DELETE' then 'suppression' else 'modification' end;
  if tg_op = 'UPDATE' and tg_table_name = 'dossiers' then
    if ancien ->> 'supprime_le' is null and nouveau ->> 'supprime_le' is not null then act := 'corbeille';
    elsif ancien ->> 'supprime_le' is not null and nouveau ->> 'supprime_le' is null then act := 'restauration';
    end if;
  end if;
  insert into public.journal (entreprise_id, user_id, table_nom, ligne_id, action, avant)
    values (eid, public.app_uid(), tg_table_name, (coalesce(nouveau, ancien) ->> 'id')::uuid, act, ancien);
  return null;
end $$;

do $$ declare t text; begin
  foreach t in array array['clients','dossiers','lignes','versements'] loop
    execute format('create trigger trg_journal after insert or update or delete on public.%I
                    for each row execute function public.journaliser()', t);
  end loop;
end $$;

-- ============ 4. Numérotation automatique ============
-- Numéro laissé vide à la création : attribué sous la forme AAAA-NNN (2026-001), par entreprise et par année.
-- Numéro saisi à la main : conservé tel quel ; s'il suit la forme AAAA-NNN, la suite repart de lui.
create table public.compteurs_dossiers (
  entreprise_id uuid not null references public.entreprises on delete cascade,
  annee integer not null,
  dernier integer not null,
  primary key (entreprise_id, annee)
);
alter table public.compteurs_dossiers enable row level security;   -- aucune règle : accès par le déclencheur seulement

create function public.numeroter_dossier() returns trigger
language plpgsql security definer set search_path = public as $$
declare a integer := extract(year from coalesce(new.date, current_date)); n integer;
begin
  -- un dossier naît maintenant, hors de la corbeille, quoi qu'envoie le site
  new.cree_le := now();
  new.supprime_le := null;
  new.supprime_par := null;
  new.numero := btrim(new.numero);
  if coalesce(new.numero, '') = '' then
    loop
      insert into public.compteurs_dossiers as c (entreprise_id, annee, dernier) values (new.entreprise_id, a, 1)
        on conflict (entreprise_id, annee) do update set dernier = c.dernier + 1
        returning c.dernier into n;
      new.numero := a || '-' || lpad(n::text, greatest(3, length(n::text)), '0');   -- 001 … 999, 1000
      exit when not exists (select 1 from public.dossiers
                            where entreprise_id = new.entreprise_id and numero = new.numero and supprime_le is null);
    end loop;
  elsif new.numero ~ ('^' || a || '-[0-9]{1,9}$') then
    n := split_part(new.numero, '-', 2)::integer;
    insert into public.compteurs_dossiers as c (entreprise_id, annee, dernier) values (new.entreprise_id, a, n)
      on conflict (entreprise_id, annee) do update set dernier = greatest(c.dernier, excluded.dernier);
  end if;
  return new;
end $$;
create trigger trg_numeroter_dossier before insert on public.dossiers
  for each row execute function public.numeroter_dossier();
alter table public.dossiers add constraint dossiers_numero_net check (numero <> '' and numero = btrim(numero));

-- ============ Vue : totaux d'un dossier (avant marge) ============
-- Chaque ligne est arrondie au franc (1,5 × 333 = 500 F), puis les lignes sont additionnées.
create view public.dossier_totaux with (security_invoker = true) as
select d.id as dossier_id, d.entreprise_id,
       coalesce((select sum(round(coalesce(l.qte, 1) * l.prix_unitaire)) from public.lignes l where l.dossier_id = d.id), 0) as total_ht_base,
       coalesce((select sum(v.montant) from public.versements v where v.dossier_id = d.id), 0) as verse,
       d.supprime_le
from public.dossiers d;

-- ============ 6. Tarifs ============
-- Le prix d'un abonnement se lit ici, jamais dans le code : un changement de prix laisse une trace.
create table public.tarifs (
  plan text not null check (plan in ('mensuel','annuel')),
  montant integer not null check (montant > 0),     -- en F CFA
  depuis date not null,
  primary key (plan, depuis)
);
insert into public.tarifs (plan, montant, depuis) values
  ('mensuel', 10000, '2026-11-11'),
  ('annuel', 100000, '2026-11-11');
alter table public.tarifs enable row level security;
create policy tar_select on public.tarifs for select using (true);

create function public.tarif_en_vigueur(p_plan text, p_date date default current_date) returns integer
language sql stable as $$
  select montant from public.tarifs where plan = p_plan and depuis <= p_date order by depuis desc limit 1
$$;

-- ============ 7. Rappels d'expiration ============
-- Une ligne par rappel envoyé : le même rappel ne part jamais deux fois.
create table public.rappels (
  id uuid primary key default gen_random_uuid(),
  abonnement_id uuid not null references public.abonnements on delete cascade,
  canal text not null check (canal in ('email','whatsapp')),
  jours_avant integer not null check (jours_avant >= 0),
  envoye_le timestamptz not null default now(),
  unique (abonnement_id, canal, jours_avant)
);
alter table public.rappels enable row level security;
create policy rap_service on public.rappels for all to service using (true) with check (true);

-- ============ Droits ============
grant usage on schema public to app, service;

-- le site
grant select on public.entreprises to app;
-- création et modification : ni l'auteur ni la date de création ne se choisissent
grant insert (id, nom, activite, slogan, adresse, tel, email, web, ninea, rc, rc_label, compte, banque,
  conditions_defaut, mode_defaut, mentions, theme, logo_path, marge_defaut, marge_sur_facture)
  on public.entreprises to app;
grant update (nom, activite, slogan, adresse, tel, email, web, ninea, rc, rc_label, compte, banque,
  conditions_defaut, mode_defaut, mentions, theme, logo_path, marge_defaut, marge_sur_facture)
  on public.entreprises to app;
grant select on public.utilisateurs, public.membres, public.abonnements, public.paiements,
                public.tarifs, public.journal, public.dossier_totaux to app;
grant select, insert, delete on public.clients to app;
grant update (nom, code, adresse, tel) on public.clients to app;
grant select, insert, update, delete on public.lignes, public.versements to app;
grant select, insert on public.dossiers to app;              -- pas de suppression définitive
-- modification : ni l'identifiant, ni l'entreprise, ni la date de création, ni l'auteur de la mise à la corbeille
grant update (numero, date, client_id, client_nom, client_adresse, client_code, marque, type, immat, km, marge_pct,
  generer_facture, date_echeance, conditions, mode, numero_br, ref_commande, incoterm, lieu, bon_commande, supprime_le)
  on public.dossiers to app;
grant execute on function public.app_uid(), public.est_membre(uuid), public.abonnement_actif(uuid),
  public.peut_ecrire(uuid), public.utilisateur_par_email(text), public.tarif_en_vigueur(text, date) to app;

-- le serveur de paiement et de rappels
grant select, insert on public.rappels to service;
grant select on public.tarifs to service;
grant execute on function public.activer_abonnement(text), public.tarif_en_vigueur(text, date) to service;

commit;
