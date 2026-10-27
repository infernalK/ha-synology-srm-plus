/*
 * Synology SRM Plus – dashboard cards
 *
 *   type: custom:synology-srm-router-card     (router health: CPU, memory, traffic, Wi-Fi, links, storage)
 *   type: custom:synology-srm-clients-card    (every client with signal, link rate, traffic and details)
 *   type: custom:synology-srm-threat-card     (threat prevention: events, new devices, admin sessions, exposure)
 *   type: custom:synology-srm-access-card    (access control: blocked IPs, Wi-Fi block list, MAC filters, blocked devices)
 *   type: custom:synology-srm-safeaccess-card (Safe Access / parental control per profile)
 *
 * Both cards find the integration's entities by themselves. Optional `device_id`
 * restricts them to one router when several are configured.
 */

const PLATFORM = 'synology_srm_plus';

const I18N = {
  en: {
    router: 'Router', uptime: 'Uptime', cpu: 'CPU', memory: 'Memory', swap: 'Swap', load: 'Load',
    connection: 'Connection', wifi_network: 'Wi-Fi network', traffic: 'Client traffic', traffic_networks: 'Traffic per Wi-Fi network', total: 'Total', wired: 'Wired', clients: 'clients', client: 'client',
    wifi: 'Wi-Fi', channel: 'Channel', signal: 'Signal', network: 'Network', external: 'External IP',
    mode: 'Mode', links: 'Links', storage: 'Storage', connection: 'Connection', ok: 'OK',
    search: 'Search a client…', all: 'All', sort: 'Sort', name: 'Name', download: 'Download',
    upload: 'Upload', nothing: 'No client', no_data: 'No Synology SRM Plus data found.', offline: 'Offline', ip: 'IP address',
    offline_clients: 'Offline clients', last_seen: 'Last seen', ago: 'ago', router_throughput: 'Router throughput', nodes: 'Wi-Fi access points', node: 'Node',
    devices: 'devices', ports: 'Ports', usb: 'USB storage', no_link: 'no link', security: 'Security', threat_prevention: 'Threat prevention', profiles: 'profiles', online: 'online', mac_filter_list: 'Wi-Fi block list', mac_filter_profiles: 'Custom MAC filters', blocked_devices: 'Blocked devices', mac_filter_networks: 'Wi-Fi with MAC filter', access_control: 'Access control', auto_block: 'Auto-block', attempts: 'attempts', per: 'in', min: 'min', no_expiry: 'no expiry', storm: 'Broadcast-storm prevention', max_pps: 'packets/s max', on: 'on', off: 'off', ip_blocked: 'Blocked IP addresses', block_list_hint: 'applies to every SSID', threats: 'Threat events',
    last24: '24 h', last7: '7 days', new_devices: 'New devices', admin_sessions: 'Admin sessions', blocked_ips: 'Blocked IPs',
    forwards: 'Port forwards', protected: 'Protected', unprotected: 'Not protected', exposed: 'Admin reachable from the Internet',
    external_session: 'Admin session from the Internet', safe: 'Safe Access', internet_time: 'Internet time',
    blocked_now: 'Blocked now', concerned: 'Concerned', normal: 'Normal', filter: 'Filter', safe_search: 'Safe search',
    quota: 'Time quota', schedule: 'Schedule', hits: 'Sites flagged', none: 'None', sort_ip: 'IP address',
    fields: {
      ip: 'IPv4', ipv6: 'IPv6', mac: 'MAC', group: 'Connection', ssid: 'SSID', wifi_profile: 'Wi-Fi profile',
      signal: 'Signal', link_rate: 'Link rate', max_link_rate: 'Max link rate', rate_quality: 'Rate quality',
      download: 'Download', upload: 'Upload', device_type: 'Device type', mesh_node: 'Router node',
      guest: 'Guest', blocked: 'Blocked', parental_control: 'Parental control', qos: 'QoS',
      high_priority: 'High priority', low_priority: 'Low priority', beamforming: 'Beamforming',
      interface: 'Interface', connection: 'Link', band: 'Band', wifi_bytes_rx: 'Wi-Fi bytes (rx)',
      wifi_bytes_tx: 'Wi-Fi bytes (tx)', last_seen: 'Last seen', safe_profile: 'Safe Access profile',
    },
  },
  fr: {
    router: 'Routeur', uptime: 'En ligne depuis', cpu: 'CPU', memory: 'Mémoire', swap: 'Swap', load: 'Charge',
    connection: 'Connexion', wifi_network: 'Réseau Wi-Fi', traffic: 'Trafic des clients', traffic_networks: 'Trafic par réseau Wi-Fi', total: 'Total', wired: 'Filaire', clients: 'clients', client: 'client',
    wifi: 'Wi-Fi', channel: 'Canal', signal: 'Signal', network: 'Réseau', external: 'IP externe',
    mode: 'Mode', links: 'Liens', storage: 'Stockage', connection: 'Connexion', ok: 'OK',
    search: 'Rechercher un client…', all: 'Tous', sort: 'Tri', name: 'Nom', download: 'Téléchargement',
    upload: 'Envoi', nothing: 'Aucun client', no_data: 'Aucune donnée Synology SRM Plus trouvée.', offline: 'Hors ligne', ip: 'Adresse IP',
    offline_clients: 'Clients hors ligne', last_seen: 'Vu il y a', ago: '', router_throughput: 'Débit du routeur', nodes: "Points d'accès Wi-Fi", node: 'Nœud',
    devices: 'appareils', ports: 'Ports', usb: 'Stockage USB', no_link: 'pas de lien', security: 'Sécurité', threat_prevention: 'Protection contre les menaces', profiles: 'profils', online: 'en ligne', mac_filter_list: 'Liste de blocage Wi-Fi', mac_filter_profiles: 'Filtres MAC perso', blocked_devices: 'Appareils bloqués', mac_filter_networks: 'Wi-Fi avec filtrage MAC', access_control: "Contrôle d'accès", auto_block: 'Blocage auto', attempts: 'tentatives', per: 'en', min: 'min', no_expiry: 'sans expiration', storm: 'Prévention des tempêtes de diffusion', max_pps: 'paquets/s max', on: 'activée', off: 'désactivée', ip_blocked: 'Adresses IP bloquées', block_list_hint: 'valable pour tous les SSID', threats: 'Menaces détectées',
    last24: '24 h', last7: '7 jours', new_devices: 'Nouveaux appareils', admin_sessions: "Sessions d'administration", blocked_ips: 'IP bloquées',
    forwards: 'Redirections de ports', protected: 'Protégé', unprotected: 'Non protégé', exposed: "Administration joignable depuis Internet",
    external_session: "Session d'administration depuis Internet", safe: 'Safe Access', internet_time: 'Temps sur internet',
    blocked_now: 'Bloqué en ce moment', concerned: 'À surveiller', normal: 'Normal', filter: 'Filtre web', safe_search: 'Recherche sécurisée',
    quota: 'Quota de temps', schedule: 'Plages horaires', hits: 'Sites signalés', none: 'Aucun', sort_ip: 'Adresse IP',
    fields: {
      ip: 'IPv4', ipv6: 'IPv6', mac: 'MAC', group: 'Connexion', ssid: 'SSID', wifi_profile: 'Profil Wi-Fi',
      signal: 'Signal', link_rate: 'Débit du lien', max_link_rate: 'Débit max du lien', rate_quality: 'Qualité du débit',
      download: 'Téléchargement', upload: 'Envoi', device_type: "Type d'appareil", mesh_node: 'Nœud du routeur',
      guest: 'Invité', blocked: 'Bloqué', parental_control: 'Contrôle parental', qos: 'QoS',
      high_priority: 'Priorité haute', low_priority: 'Priorité basse', beamforming: 'Beamforming',
      interface: 'Interface', connection: 'Lien', band: 'Bande', wifi_bytes_rx: 'Octets Wi-Fi (rx)',
      wifi_bytes_tx: 'Octets Wi-Fi (tx)', last_seen: 'Dernière connexion', safe_profile: 'Profil Safe Access',
    },
  },
};

const ICONS = {
  nas: 'mdi:nas', tablet: 'mdi:tablet', phone: 'mdi:cellphone', mobile: 'mdi:cellphone',
  smartphone: 'mdi:cellphone', notebook: 'mdi:laptop', laptop: 'mdi:laptop', pc: 'mdi:desktop-tower-monitor',
  computer: 'mdi:desktop-tower-monitor', desktop: 'mdi:desktop-tower-monitor', tv: 'mdi:television',
  television: 'mdi:television', camera: 'mdi:cctv', ipcam: 'mdi:cctv', printer: 'mdi:printer',
  speaker: 'mdi:speaker-wireless', game: 'mdi:gamepad-variant', console: 'mdi:gamepad-variant',
  watch: 'mdi:watch', router: 'mdi:router-wireless', iot: 'mdi:chip', light: 'mdi:lightbulb',
  plug: 'mdi:power-plug', default: 'mdi:devices',
};

const esc = (value) =>
  String(value ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

function strings(hass) {
  const lang = (hass && (hass.language || (hass.locale && hass.locale.language))) || 'en';
  return I18N[lang.slice(0, 2)] || I18N.en;
}

// Home Assistant shows these sensors in their display unit (Mbit/s, h...), so read the unit.
const RATE_UNITS = { 'bit/s': 1 / 8, 'kbit/s': 125, 'Mbit/s': 125000, 'Gbit/s': 125000000, 'B/s': 1, 'kB/s': 1000, 'MB/s': 1e6, 'GB/s': 1e9, 'KiB/s': 1024, 'MiB/s': 1048576, 'GiB/s': 1073741824 };
function rateOf(stateObj) {
  const value = Number(stateObj && stateObj.state);
  if (!Number.isFinite(value)) return 0;
  const unit = stateObj.attributes && stateObj.attributes.unit_of_measurement;
  return value * (RATE_UNITS[unit] ?? 1);
}

function minutesOf(stateObj) {
  const value = Number(stateObj && stateObj.state);
  if (!Number.isFinite(value)) return NaN;
  const unit = stateObj.attributes && stateObj.attributes.unit_of_measurement;
  return value * ({ s: 1 / 60, min: 1, h: 60, d: 1440 }[unit] ?? 1);
}

function fmtRate(bytesPerSecond) {
  const bits = (Number(bytesPerSecond) || 0) * 8;
  if (bits >= 1e6) return `${(bits / 1e6).toFixed(bits >= 1e7 ? 0 : 1)} Mbit/s`;
  if (bits >= 1e3) return `${Math.round(bits / 1e3)} kbit/s`;
  return bits > 0 ? `${Math.round(bits)} bit/s` : '0';
}

function fmtDuration(stateObj) {
  const value = Number(stateObj && stateObj.state);
  if (!Number.isFinite(value)) return '';
  const unit = (stateObj.attributes && stateObj.attributes.unit_of_measurement) || 'h';
  const seconds = { s: 1, min: 60, h: 3600, d: 86400 }[unit] * value;
  const d = Math.floor(seconds / 86400);
  const h = Math.floor((seconds % 86400) / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  return d ? `${d} d ${h} h` : `${h} h ${String(m).padStart(2, '0')} min`;
}

function ago(iso) {
  const then = Date.parse(iso);
  if (!Number.isFinite(then)) return '';
  const minutes = Math.max(0, Math.round((Date.now() - then) / 60000));
  if (minutes < 60) return `${minutes} min`;
  const hours = Math.round(minutes / 60);
  if (hours < 48) return `${hours} h`;
  return `${Math.round(hours / 24)} d`;
}

const mapBy = (list, key) => Object.fromEntries((list || []).map((st) => [st.attributes[key], st]));

function isPublicIp(address) {
  const a = String(address || '').split('%')[0];
  if (a.includes(':')) return !/^(fe80|fc|fd|::1)/i.test(a) && a.length > 3;
  const p = a.split('.').map(Number);
  if (p.length !== 4 || p.some((n) => !Number.isFinite(n))) return false;
  return !(p[0] === 10 || p[0] === 127 || (p[0] === 172 && p[1] >= 16 && p[1] <= 31) || (p[0] === 192 && p[1] === 168) || (p[0] === 169 && p[1] === 254));
}

function fmtState(hass, stateObj) {
  if (!stateObj) return '';
  if (typeof hass.formatEntityState === 'function') return hass.formatEntityState(stateObj);
  const unit = stateObj.attributes.unit_of_measurement;
  return unit ? `${stateObj.state} ${unit}` : stateObj.state;
}

function level(value, warn = 60, bad = 85) {
  if (value >= bad) return 'var(--error-color, #db4437)';
  if (value >= warn) return 'var(--warning-color, #ffa600)';
  return 'var(--success-color, #43a047)';
}

/** Entities of this integration, grouped by translation_key. */
function integrationEntities(hass, deviceId) {
  const out = {};
  const registry = hass.entities || {};
  for (const entry of Object.values(registry)) {
    if (entry.platform !== PLATFORM) continue;
    if (deviceId && entry.device_id !== deviceId) continue;
    const state = hass.states[entry.entity_id];
    if (!state) continue;
    const key = entry.translation_key || entry.entity_id;
    (out[key] ||= []).push(state);
  }
  return out;
}

/** Same, one group per router (device), sorted by name. */
function integrationDevices(hass, deviceId) {
  const byDevice = new Map();
  for (const entry of Object.values(hass.entities || {})) {
    if (entry.platform !== PLATFORM) continue;
    if (deviceId && entry.device_id !== deviceId) continue;
    if (!entry.device_id) continue; // device trackers have no router device: not a router card
    const state = hass.states[entry.entity_id];
    if (!state) continue;
    const found = byDevice.get(entry.device_id) || {};
    byDevice.set(entry.device_id, found);
    (found[entry.translation_key || entry.entity_id] ||= []).push(state);
  }
  const nameOf = (id) => {
    const device = (hass.devices || {})[id];
    return (device && (device.name_by_user || device.name)) || '';
  };
  return [...byDevice].map(([id, found]) => ({ id, found, name: nameOf(id) })).sort((a, b) => a.name.localeCompare(b.name));
}

const STYLE = `
  .chiplabel { opacity: .6; font-size: .75em; align-self: center; margin-right: 2px; }
  :host { display: block; min-width: 0; }
  ha-card { padding: 16px; min-width: 0; box-sizing: border-box; overflow: hidden; }
  .head { display: flex; align-items: center; gap: 12px; margin-bottom: 12px; }
  .head ha-icon { --mdc-icon-size: 32px; color: var(--primary-color); }
  .title { font-size: 1.25em; font-weight: 500; line-height: 1.2; }
  .sub { color: var(--secondary-text-color); font-size: .9em; }
  .badges { margin-left: auto; display: flex; gap: 6px; flex-wrap: wrap; justify-content: flex-end; }
  .badge { font-size: .75em; padding: 2px 8px; border-radius: 10px; color: #fff; background: var(--success-color, #43a047); }
  .badge.bad { background: var(--error-color, #db4437); }
  h3 { margin: 16px 0 8px; font-size: .8em; text-transform: uppercase; letter-spacing: .06em; color: var(--secondary-text-color); font-weight: 600; }
  .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 8px; }
  .tile { background: var(--secondary-background-color, rgba(127,127,127,.12)); border-radius: 10px; padding: 10px; cursor: pointer; min-width: 0; }
  .tile .k { color: var(--secondary-text-color); font-size: .78em; }
  .tile .v { font-size: 1.05em; font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .tile .s { color: var(--secondary-text-color); font-size: .78em; overflow-wrap: anywhere; }
  .gauges { display: grid; grid-template-columns: repeat(auto-fit, minmax(90px, 1fr)); gap: 8px; text-align: center; }
  .gauge { cursor: pointer; }
  .ring { width: 84px; height: 84px; }
  .ring .bg { fill: none; stroke: var(--divider-color, rgba(127,127,127,.3)); stroke-width: 7; }
  .ring .fg { fill: none; stroke-width: 7; stroke-linecap: round; transition: stroke-dasharray .5s; }
  .ring text { fill: var(--primary-text-color); font-size: 17px; font-weight: 500; }
  .gauge .lbl { color: var(--secondary-text-color); font-size: .8em; }
  .bar { height: 6px; border-radius: 3px; background: var(--divider-color, rgba(127,127,127,.3)); margin-top: 6px; overflow: hidden; }
  .bar > span { display: block; height: 100%; }
  .down { color: var(--info-color, #2196f3); }
  .up { color: var(--accent-color, #ff9800); }
  .empty { color: var(--secondary-text-color); padding: 12px 0; text-align: center; }

  /* clients card */
  .controls { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; margin-bottom: 8px; }
  .chips { display: flex; gap: 6px; flex-wrap: wrap; }
  .chip { border: 1px solid var(--divider-color); background: none; color: var(--primary-text-color); border-radius: 14px; padding: 3px 10px; cursor: pointer; font: inherit; font-size: .85em; }
  .chip.on { background: var(--primary-color); color: var(--text-primary-color, #fff); border-color: var(--primary-color); }
  input.search, select.sort { font: inherit; padding: 6px 10px; border-radius: 8px; border: 1px solid var(--divider-color); background: var(--card-background-color); color: var(--primary-text-color); min-width: 0; }
  input.search { flex: 1 1 150px; }
  .list { overflow-y: auto; }
  .row { display: grid; grid-template-columns: 36px 1fr auto; gap: 10px; align-items: center; padding: 8px 4px; border-bottom: 1px solid var(--divider-color); cursor: pointer; }
  .row:last-child { border-bottom: none; }
  .row.off { opacity: .6; }
  .row .ico { display: flex; flex-direction: column; align-items: center; gap: 2px; color: var(--secondary-text-color); }
  .row .ico ha-icon { --mdc-icon-size: 24px; }
  .row .nm { font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .row .meta { color: var(--secondary-text-color); font-size: .8em; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .row .rt { text-align: right; font-size: .85em; white-space: nowrap; }
  .sig { display: inline-flex; align-items: flex-end; gap: 2px; height: 12px; }
  .sig i { width: 3px; background: var(--divider-color); border-radius: 1px; }
  .detail { grid-column: 1 / -1; display: grid; grid-template-columns: repeat(auto-fill, minmax(170px, 1fr)); gap: 4px 12px; padding: 6px 0 2px 46px; font-size: .82em; cursor: default; }
  .detail b { color: var(--secondary-text-color); font-weight: 500; display: block; font-size: .85em; }
  .detail span { overflow-wrap: anywhere; }
`;

const CARDS_VERSION = '0.5.21'; // keep in sync with const.py VERSION (tests/smoke.py checks it)
// eslint-disable-next-line no-console
console.info(`Synology SRM Plus cards v${CARDS_VERSION}`);

class SrmBaseCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
  }

  setConfig(config) {
    this._config = { ...config };
    this._built = false;
    this._sig = null;
    if (this._hass) this._update();
  }

  set hass(hass) {
    this._hass = hass;
    this._update();
  }

  getCardSize() {
    return 6;
  }

  _moreInfo(entityId) {
    if (!entityId) return;
    this.dispatchEvent(new CustomEvent('hass-more-info', { detail: { entityId }, bubbles: true, composed: true }));
  }
}

/* ------------------------------------------------------------------ router card */

class SynologySrmRouterCard extends SrmBaseCard {
  static getStubConfig() {
    return {};
  }

  _update() {
    const hass = this._hass;
    if (!hass || !this._config) return;
    const devices = integrationDevices(hass, this._config.device_id);
    const sig = devices.map((d) => Object.values(d.found).flat().map((s) => s.entity_id + s.last_updated).join('|')).join('#') + (hass.language || '');
    if (sig === this._sig) return;
    this._sig = sig;
    this._render(devices);
  }

  /** One card per router when several are configured (and no device_id is set). */
  _render(devices) {
    const hass = this._hass;
    const multiple = devices.length > 1;
    const html = devices.map((d) => this._cardHtml(d.found, multiple ? d.name : '')).join('<div style="height:8px"></div>');
    this.shadowRoot.innerHTML = `<style>${STYLE}</style>${html || this._cardHtml({}, '')}`;
    this.shadowRoot.querySelectorAll('[data-entity]').forEach((el) =>
      el.addEventListener('click', () => this._moreInfo(el.dataset.entity)));
  }

  _cardHtml(found, deviceName) {
    const hass = this._hass;
    const t = strings(hass);
    const isNode = (st, n) => String(st.attributes.node) === String(n);
    const known = (st) => st && !['unknown', 'unavailable', ''].includes(st.state);
    const first = (key) => {
      const list = found[key] || [];
      return list.find((st) => isNode(st, 0) && known(st)) || list.find(known) || list.find((st) => isNode(st, 0)) || list[0];
    };
    const all = (key) => found[key] || [];
    const bandRx = mapBy(all('band_rx'), 'band');
    const bandTx = mapBy(all('band_tx'), 'band');
    const tile = (label, stateObj, extra = '') =>
      known(stateObj)
        ? `<div class="tile" data-entity="${esc(stateObj.entity_id)}"><div class="k">${esc(label)}</div><div class="v">${esc(fmtState(hass, stateObj))}</div>${extra ? `<div class="s">${extra}</div>` : ''}</div>`
        : '';
    const gauge = (label, stateObj, warn, bad) => {
      if (!stateObj || isNaN(Number(stateObj.state))) return '';
      const v = Math.max(0, Math.min(100, Number(stateObj.state)));
      const c = 2 * Math.PI * 34;
      return `<div class="gauge" data-entity="${esc(stateObj.entity_id)}"><svg viewBox="0 0 80 80" class="ring"><circle cx="40" cy="40" r="34" class="bg"/><circle cx="40" cy="40" r="34" class="fg" stroke="${level(v, warn, bad)}" stroke-dasharray="${(c * v) / 100} ${c}" transform="rotate(-90 40 40)"/><text x="40" y="46" text-anchor="middle">${Math.round(v)}%</text></svg><div class="lbl">${esc(label)}</div></div>`;
    };

    if (!Object.keys(found).length) {
      return `<ha-card><div class="empty">${esc(t.no_data)}</div></ha-card>`;
    }

    const model = first('model');
    const firmware = first('firmware');
    const uptime = first('uptime');
    const statuses = all('connection_status');
    const badges = statuses
      .map((s) => {
        const family = (s.attributes.family || '').toString().toUpperCase() || (s.attributes.ip && s.attributes.ip.includes(':') ? 'IPv6' : 'IPv4');
        const good = s.state === 'normal';
        return `<span class="badge ${good ? '' : 'bad'}" data-entity="${esc(s.entity_id)}">${esc(family)} ${good ? esc(t.ok) : esc(s.state)}</span>`;
      })
      .join('');

    const sub = [firmware && firmware.state, uptime && `${t.uptime} ${fmtDuration(uptime)}`].filter(Boolean).join(' · ');

    // traffic: Total first, then groups
    const rx = Object.fromEntries(all('client_rx').map((s) => [s.attributes.group, s]));
    const tx = Object.fromEntries(all('client_tx').map((s) => [s.attributes.group, s]));
    const groupSensors = all('clients_group');
    // traffic_by: bands | networks | both (default); Total and Wired are always shown
    const trafficBy = this._config.traffic_by;
    const showBands = trafficBy !== 'networks';
    const showNetworks = trafficBy !== 'bands';
    const groupOrder = ['Total', ...Object.keys(rx).filter((g) => g !== 'Total').sort()];
    const trafficTiles = groupOrder
      .filter((g) => rx[g] || tx[g])
      .filter((g) => showBands || g === 'Total' || g === 'Wired')
      .map((g) => {
        const count = g === 'Total' ? first('clients_online') : groupSensors.find((s) => s.attributes.group === g);
        const label = g === 'Total' ? t.total : g === 'Wired' ? t.wired : `${t.wifi} ${g}`;
        const n = count ? ` · ${esc(count.state)} ${Number(count.state) === 1 ? t.client : t.clients}` : '';
        return `<div class="tile" data-entity="${esc((rx[g] || tx[g]).entity_id)}"><div class="k">${esc(label)}${n}</div><div class="v"><span class="down">↓ ${fmtRate(rateOf(rx[g]))}</span></div><div class="v"><span class="up">↑ ${fmtRate(rateOf(tx[g]))}</span></div></div>`;
      })
      .join('');

    // traffic per Wi-Fi network (SRM profile such as "IOT"), which can span several bands
    const netRx = Object.fromEntries(all('network_rx').map((s) => [s.attributes.network, s]));
    const netTx = Object.fromEntries(all('network_tx').map((s) => [s.attributes.network, s]));
    const netCount = Object.fromEntries(all('clients_network').map((s) => [s.attributes.network, s]));
    const networkTiles = (showNetworks ? [...new Set([...Object.keys(netRx), ...Object.keys(netTx)])] : [])
      .sort()
      .filter((n) => netCount[n] && Number(netCount[n].state) > 0)
      .map((n) => {
        const c = netCount[n];
        const bands = (c.attributes.bands || []).join(' · ');
        return `<div class="tile" data-entity="${esc((netRx[n] || netTx[n]).entity_id)}"><div class="k">${esc(t.wifi)} ${esc(n)} · ${esc(c.state)} ${Number(c.state) === 1 ? t.client : t.clients}</div><div class="v"><span class="down">↓ ${fmtRate(rateOf(netRx[n]))}</span></div><div class="v"><span class="up">↑ ${fmtRate(rateOf(netTx[n]))}</span></div>${bands ? `<div class="s">${esc(bands)}</div>` : ''}</div>`;
      })
      .join('');

    // wi-fi bands
    const wifiTiles = groupSensors
      .filter((s) => s.attributes.group && !['Wired', 'Offline'].includes(s.attributes.group))
      .map((s) => {
        const a = s.attributes;
        const lines = [
          a.channel != null ? `${t.channel} ${esc(a.channel)}` : '',
          a.average_signal != null ? `${t.signal} ${esc(a.average_signal)}%` : '',
          (a.ssids || []).map(esc).join(', '),
          bandRx[s.attributes.group] || bandTx[s.attributes.group]
            ? `rx ${fmtRate(rateOf(bandRx[s.attributes.group]))} · tx ${fmtRate(rateOf(bandTx[s.attributes.group]))}`
            : '',
        ].filter(Boolean);
        return `<div class="tile" data-entity="${esc(s.entity_id)}"><div class="k">${esc(t.wifi)} ${esc(a.group)}</div><div class="v">${esc(s.state)} ${Number(s.state) === 1 ? t.client : t.clients}</div><div class="s">${lines.join(' · ')}</div></div>`;
      })
      .join('');

    // network
    const mode = first('network_mode');
    const ext4 = first('external_ipv4');
    const ext6 = first('external_ipv6');
    const speeds = Object.fromEntries(all('link_speed').map((s) => [s.attributes.interface, s]));
    const lstat = Object.fromEntries(all('link_status').map((s) => [s.attributes.interface, s]));
    const lip = Object.fromEntries(all('link_ip').map((s) => [s.attributes.interface, s]));
    const links = [...new Set([...Object.keys(speeds), ...Object.keys(lstat)])]
      .sort()
      .map((i) => {
        const st = lstat[i];
        const up = !st || st.state === 'connected';
        const detail = [speeds[i] && fmtState(hass, speeds[i]), lip[i] && lip[i].state !== 'unknown' && lip[i].state].filter(Boolean).join(' · ');
        return `<div class="tile" data-entity="${esc((st || speeds[i]).entity_id)}"><div class="k">${esc(i)}</div><div class="v" style="color:${up ? 'inherit' : 'var(--error-color,#db4437)'}">${esc(st ? st.state : '')}</div><div class="s">${esc(detail)}</div></div>`;
      })
      .join('');

    // storage
    const storage = all('storage_utilization')
      .map((s) => {
        const v = Number(s.state);
        if (isNaN(v) || v === 0) return ''; // routers without storage report 0 %
        return `<div class="tile" data-entity="${esc(s.entity_id)}"><div class="k">${esc(s.attributes.kind || '')} ${esc(s.attributes.device || '')}</div><div class="v">${v}%</div><div class="bar"><span style="width:${Math.min(100, v)}%;background:${level(v, 70, 90)}"></span></div></div>`;
      })
      .join('');

    const load = [first('load_1min'), first('load_5min'), first('load_15min')].filter(Boolean);

    // router throughput (sees offloaded traffic), bands, ports, USB
    const rrx = first('router_rx');
    const rtx = first('router_tx');
    const conn = first('connected_devices');
    const routerTile = rrx || rtx
      ? `<div class="tile" data-entity="${esc((rrx || rtx).entity_id)}"><div class="k">${esc(t.router_throughput)}${conn ? ` · ${esc(conn.state)} ${t.devices}` : ''}</div><div class="v">rx ${fmtRate(rateOf(rrx))}</div><div class="v">tx ${fmtRate(rateOf(rtx))}</div></div>`
      : '';
    // ports, grouped per router node (one sub-heading per router when there are several)
    const nodePorts = (n) => all('port_speed')
      .filter((st) => isNode(st, n))
      .sort((a, b) => (a.attributes.port === 'WAN' ? '' : String(a.attributes.port)).localeCompare(b.attributes.port === 'WAN' ? '' : String(b.attributes.port)));
    const portNodes = [...new Set(all('port_speed').map((st) => String(st.attributes.node)))].sort((a, b) => Number(a) - Number(b));
    const nodeName = (n) => {
      const ns = all('node_status').find((st) => isNode(st, n));
      return (ns && ns.attributes.name) || (String(n) === '0' ? deviceName || t.router : `${t.node} ${n}`);
    };
    const portSpeeds = portNodes
      .map((n) => {
        const tiles = nodePorts(n)
          .map((st) => {
            const linked = st.attributes.link !== false && Number(st.state) > 0;
            return `<div class="tile" data-entity="${esc(st.entity_id)}" style="${linked ? '' : 'opacity:.55'}"><div class="k">${esc(st.attributes.port)}</div><div class="v">${linked ? esc(fmtState(hass, st)) : esc(t.no_link)}</div></div>`;
          })
          .join('');
        const head = portNodes.length > 1 ? `<div class="sub" style="margin:8px 0 4px;font-weight:600">${esc(nodeName(n))}</div>` : '';
        return tiles ? `${head}<div class="grid">${tiles}</div>` : '';
      })
      .join('');
    const usbUsed = mapBy(all('usb_used'), 'volume');
    const usbTotal = mapBy(all('usb_total'), 'volume');
    const usb = all('usb_usage')
      .map((st) => {
        const v = Number(st.state);
        if (isNaN(v)) return '';
        const vol = st.attributes.volume;
        const sizes = [usbUsed[vol], usbTotal[vol]].filter(Boolean).map((x) => fmtState(hass, x)).join(' / ');
        return `<div class="tile" data-entity="${esc(st.entity_id)}"><div class="k">USB ${esc(vol)}</div><div class="v">${v}%</div><div class="s">${esc(sizes)}</div><div class="bar"><span style="width:${Math.min(100, v)}%;background:${level(v, 80, 95)}"></span></div></div>`;
      })
      .join('');

    // other router nodes (Wi-Fi access points such as a repeater)
    const nodeEntity = (key, n) => (found[key] || []).find((st) => isNode(st, n) && st.attributes.band === undefined);
    const nodeTiles = all('node_status')
      .filter((st) => !isNode(st, 0))
      .sort((a, b) => Number(a.attributes.node) - Number(b.attributes.node))
      .map((st) => {
        const n = st.attributes.node;
        const good = st.state === 'good';
        const nrx = nodeEntity('router_rx', n);
        const ntx = nodeEntity('router_tx', n);
        const ncount = nodeEntity('connected_devices', n);
        const nup = nodeEntity('uptime', n);
        const lines = [
          [nodeEntity('model', n), nodeEntity('firmware', n)].filter(Boolean).map((x) => x.state).join(' · '),
          nup && `${t.uptime} ${fmtDuration(nup)}`,
          ncount && `${ncount.state} ${t.devices}`,
          nrx || ntx ? `↓ ${fmtRate(rateOf(nrx))} · ↑ ${fmtRate(rateOf(ntx))}` : '',
        ].filter(Boolean);
        return `<div class="tile" data-entity="${esc(st.entity_id)}"><div class="k">${esc(st.attributes.name || `${t.node} ${n}`)}</div><div class="v" style="color:${good ? 'inherit' : 'var(--error-color,#db4437)'}">${esc(good ? t.ok : st.state)}</div><div class="s">${lines.map(esc).join('<br>')}</div></div>`;
      })
      .join('');

    return `
      <ha-card>
        <div class="head">
          <ha-icon icon="mdi:router-wireless"></ha-icon>
          <div><div class="title">${esc(this._config.title || deviceName || (model ? model.state : t.router))}</div><div class="sub">${esc(sub)}</div></div>
          <div class="badges">${badges}</div>
        </div>
        <div class="gauges">${gauge(t.cpu, first('cpu_usage'), 60, 85)}${gauge(t.memory, first('memory_usage'), 70, 90)}${gauge(t.swap, first('swap_usage'), 40, 70)}</div>
        ${load.length ? `<div class="sub" style="text-align:center;margin-top:4px" data-entity="${esc(load[0].entity_id)}">${esc(t.load)} ${load.map((s) => Number(s.state).toFixed(2)).join(' · ')}</div>` : ''}
        ${routerTile || trafficTiles ? `<h3>${esc(t.traffic)}</h3><div class="grid">${routerTile}${trafficTiles}</div>` : ''}
        ${networkTiles ? `<h3>${esc(t.traffic_networks)}</h3><div class="grid">${networkTiles}</div>` : ''}
        ${wifiTiles ? `<h3>${esc(t.wifi)}</h3><div class="grid">${wifiTiles}</div>` : ''}
        ${nodeTiles ? `<h3>${esc(t.nodes)}</h3><div class="grid">${nodeTiles}</div>` : ''}
        <h3>${esc(t.network)}</h3>
        <div class="grid">${tile(t.external, ext4)}${tile('IPv6', ext6)}${tile(t.mode, mode)}${tile(t.offline_clients, first('clients_offline'))}${links}</div>${portSpeeds ? `<h3>${esc(t.ports)}</h3>${portSpeeds}` : ''}
        ${usb || storage ? `<h3>${esc(t.storage)}</h3><div class="grid">${usb}${storage}</div>` : ''}
        <div class="sub" style="text-align:right;opacity:.5;font-size:.7em;margin-top:8px">cards v${CARDS_VERSION} · ${all('node_status').length} nodes · ${all('port_speed').length} ports</div>
      </ha-card>`;
  }
}

/* ------------------------------------------------------------------ clients card */

class SynologySrmClientsCard extends SrmBaseCard {
  static getStubConfig() {
    return {};
  }

  setConfig(config) {
    super.setConfig(config);
    this._filter = this._filter || 'all';
    this._network = this._network || 'all';
    this._search = this._search || '';
    this._sort = config.sort_by || this._sort || 'download';
    this._open = this._open || new Set();
  }

  getCardSize() {
    return 8;
  }

  _groups() {
    const hass = this._hass;
    const deviceId = this._config.device_id;
    const out = [];
    const registry = hass.entities || {};
    for (const state of Object.values(hass.states)) {
      if (!state.entity_id.startsWith('sensor.')) continue;
      const a = state.attributes;
      if (a.integration !== PLATFORM || !Array.isArray(a.clients) || !a.group) continue;
      const entry = registry[state.entity_id];
      if (deviceId && entry && entry.device_id !== deviceId) continue;
      out.push(state);
    }
    return out;
  }

  _update() {
    const hass = this._hass;
    if (!hass || !this._config) return;
    const groups = this._groups();
    const sig = groups.map((s) => s.entity_id + s.last_updated).join('|') + (hass.language || '');
    if (this._built && sig === this._sig) return;
    this._sig = sig;
    this._groupStates = groups;
    if (!this._built) this._build();
    this._refresh();
  }

  _build() {
    const t = strings(this._hass);
    this.shadowRoot.innerHTML = `<style>${STYLE}</style>
      <ha-card>
        <div class="head"><ha-icon icon="mdi:lan-connect"></ha-icon><div><div class="title" id="title"></div><div class="sub" id="sub"></div></div></div>
        <div class="controls">
          <div id="chiprows"></div>
          <input class="search" id="search" type="search" placeholder="${esc(t.search)}" value="${esc(this._search)}" />
          <select class="sort" id="sort" title="${esc(t.sort)}">
            <option value="download">↓ ${esc(t.download)}</option><option value="upload">↑ ${esc(t.upload)}</option>
            <option value="signal">${esc(t.signal)}</option><option value="ip">${esc(t.ip)}</option><option value="last_seen">${esc(t.last_seen.replace(/ ago$/, ''))}</option><option value="name">${esc(t.name)}</option>
          </select>
        </div>
        <div class="list" id="list"></div>
      </ha-card>`;
    const root = this.shadowRoot;
    root.getElementById('sort').value = this._sort;
    root.getElementById('search').addEventListener('input', (e) => {
      this._search = e.target.value;
      this._refresh();
    });
    root.getElementById('sort').addEventListener('change', (e) => {
      this._sort = e.target.value;
      this._refresh();
    });
    root.addEventListener('click', (e) => {
      const chip = e.target.closest('.chip');
      if (chip) {
        if (chip.dataset.network !== undefined) this._network = chip.dataset.network;
        else {
          this._filter = chip.dataset.group;
          if (this._filter === 'Offline') this._network = 'all'; // offline clients carry no network
        }
        this._refresh();
        return;
      }
      if (e.target.closest('.detail')) return;
      const row = e.target.closest('.row');
      if (row) {
        const mac = row.dataset.mac;
        this._open.has(mac) ? this._open.delete(mac) : this._open.add(mac);
        this._refresh();
      }
    });
    root.addEventListener('dblclick', (e) => {
      const row = e.target.closest('.row');
      if (row && row.dataset.entity) this._moreInfo(row.dataset.entity);
    });
    this._built = true;
    if (this._config.max_height) root.getElementById('list').style.maxHeight = `${Number(this._config.max_height)}px`;
  }

  _refresh() {
    const hass = this._hass;
    const t = strings(hass);
    const root = this.shadowRoot;
    const wanted = this._config.groups;
    let states = this._groupStates || [];
    if (Array.isArray(wanted) && wanted.length) states = states.filter((s) => wanted.includes(s.attributes.group));

    const clients = [];
    const offlineClients = [];
    for (const s of states) {
      const isOffline = s.attributes.group === 'Offline';
      for (const c of s.attributes.clients) (isOffline ? offlineClients : clients).push({ ...c, _entity: s.entity_id });
    }
    const hasOffline = states.some((s) => s.attributes.group === 'Offline');
    const labelOf = (g) => (g === 'Wired' ? t.wired : g === 'Offline' ? t.offline : `${t.wifi} ${g}`);
    const groupNames = [...new Set(states.filter((s) => s.attributes.group !== 'Offline').map((s) => s.attributes.group))].sort();
    // filter_by: both (default) | connection | network
    const filterBy = this._config.filter_by;
    const showConnection = filterBy !== 'network';
    const showNetwork = filterBy !== 'connection';
    const networkNames = [...new Set(clients.map((c) => c.wifi_profile).filter(Boolean))].sort();
    const filters = ['all', ...groupNames, ...(hasOffline ? ['Offline'] : [])];
    if (!showConnection || !filters.includes(this._filter)) this._filter = 'all';
    if (!showNetwork || !networkNames.includes(this._network)) this._network = 'all';
    const inConn = (c, g) => g === 'all' || c.group === g;
    const inNet = (c, n) => n === 'all' || c.wifi_profile === n;

    const sum = (field) => clients.reduce((a, c) => a + (Number(c[field]) || 0), 0);
    root.getElementById('title').textContent = this._config.title || 'Synology SRM';
    root.getElementById('sub').innerHTML =
      `${clients.length} ${clients.length === 1 ? t.client : t.clients} · <span class="down">↓ ${fmtRate(sum('download'))}</span> · <span class="up">↑ ${fmtRate(sum('upload'))}</span>`;

    const count = (g) => (g === 'Offline' ? offlineClients.length : clients.filter((c) => inConn(c, g) && inNet(c, this._network)).length);
    const netCount = (n) => (this._filter === 'Offline' ? 0 : clients.filter((c) => inNet(c, n) && inConn(c, this._filter)).length);
    const connectionRow = showConnection
      ? `<div class="chips"><span class="chiplabel">${esc(t.connection)}</span>${filters
          .map((g) => `<button class="chip ${this._filter === g ? 'on' : ''}" data-group="${esc(g)}">${esc(g === 'all' ? t.all : labelOf(g))} ${count(g)}</button>`)
          .join('')}</div>`
      : '';
    const networkRow = showNetwork && networkNames.length
      ? `<div class="chips"><span class="chiplabel">${esc(t.wifi_network)}</span>${['all', ...networkNames]
          .map((n) => `<button class="chip ${this._network === n ? 'on' : ''}" data-network="${esc(n)}">${esc(n === 'all' ? t.all : n)} ${netCount(n)}</button>`)
          .join('')}</div>`
      : '';
    root.getElementById('chiprows').innerHTML = connectionRow + networkRow;

    const q = this._search.trim().toLowerCase();
    const pool = this._filter === 'Offline' ? offlineClients : clients.filter((c) => inConn(c, this._filter) && inNet(c, this._network));
    let rows = pool.filter((c) => !q || [c.name, c.ip, c.mac, c.ssid, c.wifi_profile, c.device_type, c.ipv6].some((v) => String(v ?? '').toLowerCase().includes(q)));
    const key = this._sort;
    const ipKey = (c) => (c.ip ? String(c.ip).split('.').reduce((a, p) => a * 256 + Number(p), 0) : Infinity);
    const byName = (a, b) => String(a.name).localeCompare(String(b.name));
    rows.sort((a, b) => {
      if (key === 'name') return byName(a, b);
      if (key === 'last_seen') return (Date.parse(b.last_seen) || 0) - (Date.parse(a.last_seen) || 0) || byName(a, b);
      if (key === 'ip') return ipKey(a) - ipKey(b) || byName(a, b);
      return (Number(b[key]) || 0) - (Number(a[key]) || 0) || byName(a, b);
    });

    const bars = (signal) => {
      const n = Math.max(0, Math.min(4, Math.ceil((Number(signal) || 0) / 25)));
      const color = n >= 3 ? 'var(--success-color,#43a047)' : n === 2 ? 'var(--warning-color,#ffa600)' : 'var(--error-color,#db4437)';
      return `<span class="sig" title="${esc(signal)}%">${[1, 2, 3, 4].map((i) => `<i style="height:${i * 3}px;${i <= n ? `background:${color}` : ''}"></i>`).join('')}</span>`;
    };

    // wired: coloured like the Wi-Fi bars, by link speed (unknown speed counts as fine)
    const cable = (rate) => {
      const r = Number(rate) || 0;
      const color = !r || r >= 1000 ? 'var(--success-color,#43a047)' : r >= 100 ? 'var(--warning-color,#ffa600)' : 'var(--error-color,#db4437)';
      return `<ha-icon icon="mdi:ethernet-cable" style="--mdc-icon-size:14px;color:${color}"></ha-icon>`;
    };

    const detailOf = (c) => {
      const skip = new Set(['name', '_entity']);
      const flat = Object.entries(c).flatMap(([k, v]) =>
        k === 'extra' && v && typeof v === 'object' ? Object.entries(v) : [[k, v]]);
      return flat
        .filter(([k, v]) => !skip.has(k) && v !== undefined && v !== null && v !== '')
        .map(([k, v]) => {
          let value = v;
          if (k === 'download' || k === 'upload') value = fmtRate(v);
          else if (k === 'link_rate' || k === 'max_link_rate') value = `${v} Mbit/s`;
          else if (k === 'signal') value = `${v}%`;
          else if (k === 'group') value = labelOf(v);
          else if (k === 'last_seen') value = new Date(v).toLocaleString();
          else if (typeof v === 'boolean') value = v ? '✔' : '✖';
          return `<div><b>${esc(t.fields[k] || k)}</b><span>${esc(value)}</span></div>`;
        })
        .join('');
    };

    root.getElementById('list').innerHTML = rows.length
      ? rows
          .map((c) => {
            const icon = ICONS[String(c.device_type || '').toLowerCase()] || ICONS.default;
            const off = c.group === 'Offline';
            const wifi = !off && c.group !== 'Wired';
            const seen = off && c.last_seen ? `${t.last_seen} ${ago(c.last_seen)} ${t.ago}`.trim() : '';
            const meta = [c.ip || c.ipv6, labelOf(c.group), c.ssid, seen].filter(Boolean).join(' · ');
            const rate = c.link_rate ? `${c.link_rate} Mbit/s` : '';
            const status = off ? '<ha-icon icon="mdi:lan-disconnect" style="--mdc-icon-size:14px"></ha-icon>' : wifi ? bars(c.signal) : cable(c.link_rate);
            return `<div class="row ${off ? 'off' : ''}" data-mac="${esc(c.mac)}" data-entity="${esc(c._entity)}">
              <div class="ico"><ha-icon icon="${icon}"></ha-icon>${status}</div>
              <div style="min-width:0"><div class="nm">${esc(c.name)}</div><div class="meta">${esc(meta)}</div></div>
              <div class="rt">${off ? `<div class="meta">${esc(t.offline)}</div>` : `<div class="down">↓ ${fmtRate(c.download)}</div><div class="up">↑ ${fmtRate(c.upload)}</div><div class="meta">${esc(rate)}</div>`}</div>
              ${this._open.has(c.mac) ? `<div class="detail">${detailOf(c)}</div>` : ''}
            </div>`;
          })
          .join('')
      : `<div class="empty">${esc(clients.length ? t.nothing : t.no_data)}</div>`;
  }
}


/* ------------------------------------------------------------------ shared: entity cards */

class SrmEntityCard extends SrmBaseCard {
  static getStubConfig() {
    return {};
  }

  _update() {
    const hass = this._hass;
    if (!hass || !this._config) return;
    const found = integrationEntities(hass, this._config.device_id);
    const sig = Object.values(found).flat().map((s) => s.entity_id + s.last_updated).join('|') + (hass.language || '');
    if (sig === this._sig) return;
    this._sig = sig;
    if (!Object.keys(found).length) {
      this.shadowRoot.innerHTML = `<style>${STYLE}</style><ha-card><div class="empty">${esc(strings(hass).no_data)}</div></ha-card>`;
      return;
    }
    this._render(found);
    this.shadowRoot.querySelectorAll('[data-entity]').forEach((el) =>
      el.addEventListener('click', () => this._moreInfo(el.dataset.entity)));
  }
}

/* ------------------------------------------------------------------ threat prevention card */

class SynologySrmThreatCard extends SrmEntityCard {
  _render(found) {
    const hass = this._hass;
    const t = strings(hass);
    const first = (key) => (found[key] || [])[0];
    const prot = first('threat_protection');
    const exposed = first('srm_exposed_wan');
    const ext = first('external_admin_session');
    const badge = (st, good, label) =>
      st ? `<span class="badge ${(st.state === 'on') === good ? '' : 'bad'}" data-entity="${esc(st.entity_id)}">${esc(label)}</span>` : '';
    const badges =
      badge(prot, true, prot && prot.state === 'on' ? t.protected : t.unprotected) +
      (exposed && exposed.state === 'on' ? badge(exposed, false, t.exposed) : '') +
      (ext && ext.state === 'on' ? badge(ext, false, t.external_session) : '');

    const tile = (label, st, sub = '') =>
      st ? `<div class="tile" data-entity="${esc(st.entity_id)}"><div class="k">${esc(label)}</div><div class="v">${esc(st.state)}</div>${sub ? `<div class="s">${sub}</div>` : ''}</div>` : '';
    const t24 = first('threat_events_24h');
    const t7 = first('threat_events_7d');
    const lv = t7 ? t7.attributes : {};
    const levels = t7 ? `high ${lv.high ?? 0} · medium ${lv.medium ?? 0} · low ${lv.low ?? 0}` : '';
    const nd = first('new_devices');
    const newNames = nd ? (nd.attributes.devices || []).map((d) => esc(d.hostname || d.name || d.mac || '?')).join(', ') : '';
    const tiles =
      tile(`${t.threats} (${t.last24})`, t24) +
      tile(`${t.threats} (${t.last7})`, t7, esc(levels)) +
      tile(t.new_devices, nd, newNames) +
      tile(t.admin_sessions, first('admin_sessions')) +
      tile(t.forwards, first('port_forward_rules'));

    const sessionsSt = first('admin_sessions');
    const sessions = sessionsSt ? (sessionsSt.attributes.sessions || []).slice(0, 8) : [];
    const sessionRows = sessions
      .map((x) => {
        const bad = isPublicIp(x.from);
        return `<div class="row" style="grid-template-columns:1fr auto;cursor:default"><div style="min-width:0"><div class="nm" style="${bad ? 'color:var(--error-color,#db4437)' : ''}">${esc(x.who || '')} · ${esc(x.from || '')}</div><div class="meta">${esc(x.descr || x.type || '')}</div></div><div class="rt meta">${esc(x.time || '')}</div></div>`;
      })
      .join('');

    this.shadowRoot.innerHTML = `<style>${STYLE}</style>
      <ha-card>
        <div class="head"><ha-icon icon="mdi:shield-check"></ha-icon><div><div class="title">${esc(this._config.title || t.threat_prevention)}</div></div><div class="badges">${badges}</div></div>
        <div class="grid">${tiles}</div>
        ${sessionRows ? `<h3>${esc(t.admin_sessions)}</h3>${sessionRows}` : ''}
      </ha-card>`;
  }
}


/* ------------------------------------------------------------------ access control card */

class SynologySrmAccessCard extends SrmEntityCard {
  _render(found) {
    const hass = this._hass;
    const t = strings(hass);
    const first = (key) => (found[key] || [])[0];
    const devs = (st) => (st && Array.isArray(st.attributes.devices) ? st.attributes.devices : []);
    const names = (st) => devs(st).map((d) => esc(d.name || d.mac || '?')).join(', ');
    const tile = (label, st, sub = '') =>
      st ? `<div class="tile" data-entity="${esc(st.entity_id)}"><div class="k">${esc(label)}</div><div class="v">${esc(st.state)}</div>${sub ? `<div class="s">${sub}</div>` : ''}</div>` : '';

    const ips = first('blocked_ips');
    const a = ips ? ips.attributes : {};
    const abLine = ips && a.auto_block_enabled !== undefined
      ? `${esc(t.auto_block)} ${a.auto_block_enabled ? esc(t.on) : esc(t.off)}${a.failed_attempts != null ? ` · ${esc(a.failed_attempts)} ${esc(t.attempts)} ${esc(t.per)} ${esc(a.within_minutes)} ${esc(t.min)}` : ''}${a.expire_days === 0 ? ` · ${esc(t.no_expiry)}` : a.expire_days ? ` · ${esc(a.expire_days)} d` : ''}`
      : '';
    const blockList = first('mac_filter_devices');
    const storm = blockList ? blockList.attributes : {};
    const stormLine = storm.broadcast_storm_prevention !== undefined && storm.broadcast_storm_prevention !== null
      ? `${esc(t.storm)}: ${storm.broadcast_storm_prevention ? esc(t.on) : esc(t.off)}${storm.max_broadcast_packets_per_second ? ` (${esc(storm.max_broadcast_packets_per_second)} ${esc(t.max_pps)})` : ''}`
      : '';
    const filters = found.wifi_mac_filter || [];
    const filterOn = filters.filter((st) => st.state === 'on');
    const networksTile = filters.length
      ? `<div class="tile" data-entity="${esc(filters[0].entity_id)}"><div class="k">${esc(t.mac_filter_networks)}</div><div class="v">${filterOn.length}</div><div class="s">${filterOn.map((st) => esc(st.attributes.network)).join(', ') || filters.map((st) => esc(st.attributes.network)).join(', ')}</div></div>`
      : '';
    const tiles =
      tile(t.ip_blocked, ips, esc(abLine)) +
      tile(t.mac_filter_list, blockList, names(blockList) || esc(t.block_list_hint)) +
      tile(t.mac_filter_profiles, first('mac_filter_profiles')) +
      networksTile +
      tile(t.blocked_devices, first('blocked_devices'), names(first('blocked_devices')));

    const row = (title, meta) =>
      `<div class="row" style="grid-template-columns:1fr auto;cursor:default"><div style="min-width:0"><div class="nm">${title}</div><div class="meta">${meta}</div></div></div>`;
    const rows =
      devs(blockList).map((d) => row(esc(d.name || d.mac), `${esc(d.mac || '')} · ${esc(t.mac_filter_list)}`)).join('') +
      devs(first('blocked_devices')).map((d) => row(esc(d.name || d.mac), `${esc(d.ip || d.mac || '')} · ${esc(t.blocked_devices)}`)).join('');
    const addresses = this._config.show_blocked_ips !== false && Array.isArray(a.addresses) ? a.addresses : [];
    const addressRows = addresses
      .map((x) => row(esc(typeof x === 'string' ? x : x.ip || x.address || JSON.stringify(x)), esc(t.ip_blocked)))
      .join('');

    this.shadowRoot.innerHTML = `<style>${STYLE}</style>
      <ha-card>
        <div class="head"><ha-icon icon="mdi:shield-lock"></ha-icon><div><div class="title">${esc(this._config.title || t.access_control)}</div><div class="sub">${stormLine}</div></div></div>
        <div class="grid">${tiles}</div>
        ${rows || addressRows ? `<div style="margin-top:8px">${addressRows}${rows}</div>` : ''}
      </ha-card>`;
  }
}

/* ------------------------------------------------------------------ Safe Access card */

class SynologySrmSafeAccessCard extends SrmEntityCard {
  _render(found) {
    const hass = this._hass;
    const t = strings(hass);
    const all = (key) => found[key] || [];
    this._open = this._open || new Set();
    const times = mapBy(all('safe_time'), 'profile');
    const status = mapBy(all('safe_status'), 'profile');
    const blocked = mapBy(all('safe_blocked'), 'profile');
    const profiles = Object.keys(times).sort((a, b) => a.localeCompare(b));
    const isConcerned = (name) => (status[name] ? status[name].state : times[name].attributes.concerned_status) === 'concerned';
    const isBlocked = (name) => blocked[name] && blocked[name].state === 'on';
    const nBlocked = profiles.filter(isBlocked).length;
    const nConcerned = profiles.filter(isConcerned).length;
    const badges =
      (nBlocked ? `<span class="badge bad">${nBlocked} ${esc(t.blocked_now.toLowerCase())}</span>` : '') +
      (nConcerned ? `<span class="badge" style="background:var(--warning-color,#ffa600)">${nConcerned} ${esc(t.concerned.toLowerCase())}</span>` : '');

    const flag = (on, icon, label) => `<span title="${esc(label)}" style="opacity:${on ? 1 : 0.25};margin-right:6px">${icon}</span>`;
    const hm = (minutes) => (Number.isFinite(minutes) ? `${Math.floor(minutes / 60)} h ${String(Math.round(minutes % 60)).padStart(2, '0')}` : '');
    const rows = profiles
      .map((name) => {
        const tm = times[name];
        const a = tm.attributes;
        const devs = Array.isArray(a.devices) ? a.devices : [];
        const nOnline = devs.filter((d) => d.online).length;
        const open = this._open.has(name);
        const hits = a.inappropriate_websites ? Object.entries(a.inappropriate_websites).map(([k, v]) => `${esc(k)} (${esc(v)})`).join(', ') : '';
        const deviceList = open
          ? `<div style="grid-column:1/-1;padding:4px 0 2px 14px">${
              devs
                .map((d) => `<div class="meta" style="opacity:${d.online ? 1 : 0.55}"><span style="color:${d.online ? 'var(--success-color,#43a047)' : 'var(--disabled-text-color,#9e9e9e)'}">●</span> ${esc(d.name)}${d.ip ? ` · ${esc(d.ip)}` : ''}${Number.isFinite(Number(d.internet_minutes)) && d.internet_minutes > 0 ? ` · ${esc(hm(Number(d.internet_minutes)))}` : ''}</div>`)
                .join('') || `<div class="meta">${esc(t.none)}</div>`
            }</div>`
          : '';
        return `<div class="row" style="grid-template-columns:1fr auto" data-profile="${esc(name)}"><div style="min-width:0"><div class="nm">${esc(name)}${isBlocked(name) ? ` <span class="badge bad">${esc(t.blocked_now)}</span>` : ''}${isConcerned(name) ? ` <span class="badge" style="background:var(--warning-color,#ffa600)">${esc(t.concerned)}</span>` : ''}</div>
          <div class="meta">${open ? '▾' : '▸'} ${devs.length} ${esc(t.devices)}${devs.length ? ` (${nOnline} ${esc(t.online)})` : ''} · ${flag(a.web_filter, '🌐', t.filter)}${flag(a.safe_search, '🔎', t.safe_search)}${flag(a.time_quota, '⏱', t.quota)}${flag(a.block_time, '🌙', t.schedule)}${hits ? `· ${esc(t.hits)}: ${hits}` : ''}</div></div>
          <div class="rt"><div>${esc(hm(minutesOf(tm)))}</div><div class="meta">${esc(t.internet_time)}</div></div>${deviceList}</div>`;
      })
      .join('');

    this.shadowRoot.innerHTML = `<style>${STYLE}</style>
      <ha-card>
        <div class="head"><ha-icon icon="mdi:account-child-circle"></ha-icon><div><div class="title">${esc(this._config.title || t.safe)}</div><div class="sub">${profiles.length} ${esc(t.profiles)}</div></div><div class="badges">${badges}</div></div>
        ${rows || `<div class="empty">${esc(t.none)}</div>`}
      </ha-card>`;
    this.shadowRoot.querySelectorAll('[data-profile]').forEach((el) =>
      el.addEventListener('click', () => {
        const name = el.dataset.profile;
        this._open.has(name) ? this._open.delete(name) : this._open.add(name);
        this._sig = null;
        this._update();
      }));
  }
}

/* ------------------------------------------------------------------ visual editors */

const EDITOR_LABELS = {
  en: {
    title: 'Title', device_id: 'Router (optional, if you have several)', traffic_by: 'Client traffic per',
    both: 'Wi-Fi band and Wi-Fi network', bands: 'Wi-Fi band', networks: 'Wi-Fi network',
    filter_by: 'Filters shown', f_both: 'Connection and Wi-Fi network', f_connection: 'Connection (band, wired)', f_network: 'Wi-Fi network', sort_by: 'Sort by', groups: 'Show only these connections', max_height: 'Maximum height (px)',
    show_blocked_ips: 'Show the list of blocked IPs', download: 'Download', upload: 'Upload', signal: 'Signal', name: 'Name', last_seen: 'Last seen',
  },
  fr: {
    title: 'Titre', device_id: 'Routeur (facultatif, si vous en avez plusieurs)', traffic_by: 'Trafic des clients par',
    both: 'Bande Wi-Fi et réseau Wi-Fi', bands: 'Bande Wi-Fi', networks: 'Réseau Wi-Fi',
    filter_by: 'Filtres affichés', f_both: 'Connexion et réseau Wi-Fi', f_connection: 'Connexion (bande, filaire)', f_network: 'Réseau Wi-Fi', sort_by: 'Trier par', groups: 'Afficher seulement ces connexions', max_height: 'Hauteur maximale (px)',
    show_blocked_ips: 'Afficher la liste des IP bloquées', download: 'Téléchargement', upload: 'Envoi', signal: 'Signal', name: 'Nom', last_seen: 'Dernière connexion',
  },
};

function editorSchema(kind, L) {
  const choice = (name, pairs) => ({ name, selector: { select: { mode: 'dropdown', options: pairs.map(([value, label]) => ({ value, label })) } } });
  const base = [{ name: 'title', selector: { text: {} } }, { name: 'device_id', selector: { device: { integration: PLATFORM } } }];
  if (kind === 'router') return [...base, choice('traffic_by', [['both', L.both], ['bands', L.bands], ['networks', L.networks]])];
  if (kind === 'clients') {
    return [
      ...base,
      choice('filter_by', [['both', L.f_both], ['connection', L.f_connection], ['network', L.f_network]]),
      choice('sort_by', [['download', L.download], ['upload', L.upload], ['signal', L.signal], ['ip', 'IP'], ['name', L.name], ['last_seen', L.last_seen]]),
      { name: 'groups', selector: { select: { multiple: true, custom_value: true, options: ['Wired', 'Offline', '2.4G', '5G', '5G-1', '5G-2'] } } },
      { name: 'max_height', selector: { number: { min: 100, max: 2000, step: 50, mode: 'box' } } },
    ];
  }
  if (kind === 'access') return [...base, { name: 'show_blocked_ips', selector: { boolean: {} } }];
  return base;
}

class SrmCardEditor extends HTMLElement {
  setConfig(config) {
    this._config = { ...config };
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    if (this._form) this._form.hass = hass;
  }

  _render() {
    const lang = ((this._hass && (this._hass.language || '')) || 'en').slice(0, 2);
    const L = EDITOR_LABELS[lang] || EDITOR_LABELS.en;
    if (!this._form) {
      this._form = document.createElement('ha-form');
      this._form.addEventListener('value-changed', (ev) => {
        ev.stopPropagation();
        const next = { ...ev.detail.value, type: this._config.type };
        for (const key of Object.keys(next)) {
          const v = next[key];
          if (v === '' || v == null || (Array.isArray(v) && !v.length)) delete next[key];
        }
        this._config = next;
        this.dispatchEvent(new CustomEvent('config-changed', { detail: { config: next }, bubbles: true, composed: true }));
      });
      this.appendChild(this._form);
    }
    this._form.hass = this._hass;
    this._form.data = this._config;
    this._form.schema = editorSchema(this.constructor.kind, L);
    this._form.computeLabel = (item) => L[item.name] || item.name;
  }
}

const EDITORS = { router: 'router', clients: 'clients', threat: 'threat', access: 'access', safeaccess: 'safeaccess' };
for (const [kind, name] of Object.entries(EDITORS)) {
  const tag = `synology-srm-${name}-card-editor`;
  if (!customElements.get(tag)) customElements.define(tag, class extends SrmCardEditor { static kind = kind; });
}
for (const [cls, name] of [[SynologySrmRouterCard, 'router'], [SynologySrmClientsCard, 'clients'], [SynologySrmThreatCard, 'threat'], [SynologySrmAccessCard, 'access'], [SynologySrmSafeAccessCard, 'safeaccess']]) {
  cls.getConfigElement = () => document.createElement(`synology-srm-${name}-card-editor`);
}


if (!customElements.get('synology-srm-access-card')) customElements.define('synology-srm-access-card', SynologySrmAccessCard);
if (!customElements.get('synology-srm-threat-card')) customElements.define('synology-srm-threat-card', SynologySrmThreatCard);
if (!customElements.get('synology-srm-safeaccess-card')) customElements.define('synology-srm-safeaccess-card', SynologySrmSafeAccessCard);
if (!customElements.get('synology-srm-router-card')) customElements.define('synology-srm-router-card', SynologySrmRouterCard);
if (!customElements.get('synology-srm-clients-card')) customElements.define('synology-srm-clients-card', SynologySrmClientsCard);

window.customCards = window.customCards || [];
window.customCards.push(
  {
    type: 'synology-srm-access-card',
    name: 'Synology SRM – Access control',
    description: 'Blocked IPs (auto-block), Wi-Fi block list, custom MAC filters and blocked devices.',
  },
  {
    type: 'synology-srm-threat-card',
    name: 'Synology SRM – Threat prevention',
    description: 'Threat events, new devices, admin sessions and exposure of the router.',
  },
  {
    type: 'synology-srm-safeaccess-card',
    name: 'Synology SRM – Safe Access',
    description: 'Parental control: internet time, status and schedules per profile.',
  },
  {
    type: 'synology-srm-router-card',
    name: 'Synology SRM – Router',
    description: 'Router health: CPU, memory, traffic, Wi-Fi, ports, USB and storage.',
  },
  {
    type: 'synology-srm-clients-card',
    name: 'Synology SRM – Clients',
    description: 'Every client with signal, link rate, traffic and details.',
  },
);
