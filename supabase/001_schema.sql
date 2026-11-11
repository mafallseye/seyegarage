-- SeyeGarage V1 : schéma PostgreSQL (Supabase)
-- Un compte (email) -> plusieurs entreprises -> chacune son abonnement, ses clients, ses dossiers.

create extension if not exists pgcrypto;

-- ============ Tables ============
create table public.entreprises (
  id uuid primary key default gen_random_uuid(),
  nom text not null,
  activite text not null default 'garage' check (activite in ('garage','menuiserie','autre')),
  slogan text, adresse text, tel text, email text, web text,
  ninea text, rc text, rc_label text default 'RCCM',
  compte text, banque text,
  conditions_defaut text, mode_defaut text, mentions text,
  theme text not null default 'classique' check (theme in ('classique','eco','charte')),
  logo_path text,
  marge_defaut numeric(5,2),               -- vide = aucune marge
  marge_sur_facture boolean not null default true,
  cree_par uuid not null default auth.uid(),
  cree_le timestamptz not null default now()
);

create table public.membres (
  entreprise_id uuid not null references public.entreprises on delete cascade,
  user_id uuid not null,
  role text not null default 'proprietaire' check (role in ('proprietaire','employe')),
  primary key (entreprise_id, user_id)
);
create index on public.membres (user_id);

create table public.abonnements (
  id uuid primary key default gen_random_uuid(),
  entreprise_id uuid not null references public.entreprises on delete cascade,
  plan text not null check (plan in ('essai','mensuel','annuel')),
  debut date not null default current_date,
  fin date not null,
  montant integer not null default 0,       -- en F CFA
  cree_le timestamptz not null default now()
);
create index on public.abonnements (entreprise_id, fin desc);

create table public.paiements (
  id uuid primary key default gen_random_uuid(),
  entreprise_id uuid not null references public.entreprises on delete cascade,
  plan text not null check (plan in ('mensuel','annuel')),
  montant integer not null,
  statut text not null default 'en_attente' check (statut in ('en_attente','paye','echoue')),
  paydunya_token text unique,
  cree_le timestamptz not null default now(),
  paye_le timestamptz
);

create table public.clients (
  id uuid primary key default gen_random_uuid(),
  entreprise_id uuid not null references public.entreprises on delete cascade,
  nom text not null, code text, adresse text, tel text,
  cree_le timestamptz not null default now()
);
create index on public.clients (entreprise_id, nom);

create table public.dossiers (
  id uuid primary key default gen_random_uuid(),
  entreprise_id uuid not null references public.entreprises on delete cascade,
  numero text not null,
  date date not null default current_date,
  client_id uuid references public.clients on delete set null,
  client_nom text not null, client_adresse text, client_code text,
  marque text, type text, immat text, km integer,
  marge_pct numeric(5,2),                   -- null = aucune
  generer_facture boolean not null default true,
  date_echeance date, conditions text, mode text,
  numero_br text, ref_commande text, incoterm text, lieu text, bon_commande text,
  cree_le timestamptz not null default now(),
  unique (entreprise_id, numero)
);
create index on public.dossiers (entreprise_id, date desc);

create table public.lignes (
  id uuid primary key default gen_random_uuid(),
  dossier_id uuid not null references public.dossiers on delete cascade,
  entreprise_id uuid not null references public.entreprises on delete cascade,
  position integer not null default 0,
  designation text not null,
  qte integer check (qte is null or qte > 0),   -- null = main d'oeuvre / forfait
  prix_unitaire numeric(14,2) not null default 0
);
create index on public.lignes (dossier_id, position);

create table public.versements (
  id uuid primary key default gen_random_uuid(),
  dossier_id uuid not null references public.dossiers on delete cascade,
  entreprise_id uuid not null references public.entreprises on delete cascade,
  date date not null default current_date,
  montant numeric(14,2) not null check (montant > 0),
  mode text
);
create index on public.versements (dossier_id);

-- ============ Fonctions d'accès ============
create or replace function public.est_membre(eid uuid) returns boolean
language sql stable security definer set search_path = public as $$
  select exists (select 1 from public.membres where entreprise_id = eid and user_id = auth.uid());
$$;

-- abonnement en cours (essai ou payant) ? sinon : lecture seule
create or replace function public.abonnement_actif(eid uuid) returns boolean
language sql stable security definer set search_path = public as $$
  select exists (select 1 from public.abonnements where entreprise_id = eid and fin >= current_date);
$$;

create or replace function public.peut_ecrire(eid uuid) returns boolean
language sql stable security definer set search_path = public as $$
  select public.est_membre(eid) and public.abonnement_actif(eid);
$$;

-- Création d'une entreprise : le créateur devient propriétaire + essai gratuit de 14 jours
create or replace function public.apres_creation_entreprise() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  insert into public.membres (entreprise_id, user_id, role) values (new.id, new.cree_par, 'proprietaire');
  insert into public.abonnements (entreprise_id, plan, debut, fin, montant)
    values (new.id, 'essai', current_date, current_date + 14, 0);
  return new;
end $$;
create trigger trg_apres_creation_entreprise after insert on public.entreprises
  for each row execute function public.apres_creation_entreprise();

-- Activation d'un abonnement payé (appelée uniquement par le serveur / webhook PayDunya)
create or replace function public.activer_abonnement(p_token text) returns void
language plpgsql security definer set search_path = public as $$
declare p public.paiements; base date; jours integer;
begin
  select * into p from public.paiements where paydunya_token = p_token for update;
  if not found or p.statut = 'paye' then return; end if;
  update public.paiements set statut = 'paye', paye_le = now() where id = p.id;
  select greatest(current_date, coalesce(max(fin), current_date)) into base
    from public.abonnements where entreprise_id = p.entreprise_id;
  insert into public.abonnements (entreprise_id, plan, debut, fin, montant)
    values (p.entreprise_id, p.plan, base,
            case p.plan when 'annuel' then (base + interval '1 year')::date else (base + interval '1 month')::date end,
            p.montant);
end $$;
revoke all on function public.activer_abonnement(text) from public, anon, authenticated;

-- ============ Sécurité (RLS) ============
alter table public.entreprises enable row level security;
alter table public.membres     enable row level security;
alter table public.abonnements enable row level security;
alter table public.paiements   enable row level security;
alter table public.clients     enable row level security;
alter table public.dossiers    enable row level security;
alter table public.lignes      enable row level security;
alter table public.versements  enable row level security;

-- entreprises
create policy ent_select on public.entreprises for select using (public.est_membre(id) or cree_par = auth.uid());
create policy ent_insert on public.entreprises for insert with check (cree_par = auth.uid());
create policy ent_update on public.entreprises for update using (public.peut_ecrire(id)) with check (public.est_membre(id));
-- membres / abonnements / paiements : lecture seule pour les membres (écritures par le serveur)
create policy mem_select on public.membres     for select using (public.est_membre(entreprise_id));
create policy abo_select on public.abonnements for select using (public.est_membre(entreprise_id));
create policy pay_select on public.paiements   for select using (public.est_membre(entreprise_id));
-- données de travail : lecture toujours (export Excel même expiré), écriture seulement si abonnement actif
do $$ declare t text; begin
  foreach t in array array['clients','dossiers','lignes','versements'] loop
    execute format('create policy %I_select on public.%I for select using (public.est_membre(entreprise_id))', t, t);
    execute format('create policy %I_insert on public.%I for insert with check (public.peut_ecrire(entreprise_id))', t, t);
    execute format('create policy %I_update on public.%I for update using (public.peut_ecrire(entreprise_id)) with check (public.peut_ecrire(entreprise_id))', t, t);
    execute format('create policy %I_delete on public.%I for delete using (public.peut_ecrire(entreprise_id))', t, t);
  end loop;
end $$;

-- ============ Vue : totaux d'un dossier (avant marge) ============
create or replace view public.dossier_totaux with (security_invoker = true) as
select d.id as dossier_id, d.entreprise_id,
       coalesce((select sum(coalesce(l.qte,1) * l.prix_unitaire) from public.lignes l where l.dossier_id = d.id),0) as total_ht_base,
       coalesce((select sum(v.montant) from public.versements v where v.dossier_id = d.id),0) as verse
from public.dossiers d;
