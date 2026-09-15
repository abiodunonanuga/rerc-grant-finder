(function () {
  "use strict";

  const SCHEMA_VERSION = 1;
  const DB_NAME = "rerc-community-planner";
  const DB_VERSION = 1;
  const WORKSPACE_STORE = "workspaces";
  const DEFAULT_WORKSPACE_ID = "local";
  const LANGUAGE_KEY = "rerc.language";
  // A browser-local ID keeps one visitor's saved plan separate from another's.
  // Do not derive this from IP address: IPs can be shared, change frequently,
  // and would require collecting personal data on a static public site.
  const LAST_WORKSPACE_KEY = "rerc.activeWorkspaceId.v2";
  const WORKSPACE_ID_PREFIX = "browser-";
  const MAX_IDS = 100;
  const MAX_COMPARE = 3;
  const MAX_NOTES = 12000;
  const MAX_FILE_BYTES = 256 * 1024;
  const MAX_SHARE_LENGTH = 1800;
  const PHASES = ["Plan", "Design", "Build", "Operate"];
  const ALLOWED_LANGUAGES = ["en", "es"];

  const TEXT = {
    en: {
      saved: "Saved",
      save: "Add to plan",
      remove: "Remove from plan",
      compare: "Compare",
      comparing: "Comparing",
      savedOnly: "Show saved only",
      savedViewCount: "{count} saved matches displayed.",
      savedViewSummary: "Your saved options are shown below. The Word and CSV controls export this saved view.",
      savedViewTitle: "Your saved options for {state}",
      savedOptionsLabel: "Saved options",
      allMatchesLabel: "All matches",
      allMatches: "Show all matches",
      noSaved: "No saved matches yet. Add options to build a plan.",
      noDeadlines: "Save funding options to see their application timing here.",
      noFundingSequence: "Save funding options to build a phase-by-phase grant strategy.",
      fundingSequence: "Funding sequence",
      fundingSequenceSummary: "{count} saved funding options, ordered from planning through operations.",
      fundingSequenceCaveat: "This is a planning sequence, not a promise of funding. Each program makes its own award decisions.",
      sequenceStep: "Step {step}",
      sequenceTiming: "Application timing",
      preparesFor: "Can prepare application materials for",
      noLaterTargets: "Build readiness for the next project phase.",
      planPurpose: "Define the project, partners, scope, community support, and early costs.",
      designPurpose: "Complete design, engineering, environmental review, permits, and firm cost estimates.",
      buildPurpose: "Fund construction, acquisition, equipment, and other capital work.",
      operatePurpose: "Support programming, staffing, maintenance, stewardship, and long-term use.",
      planOutputs: "Useful outputs: project plan, partner roles, public input, feasibility findings, and a preliminary budget.",
      designOutputs: "Useful outputs: final plans, permits, site control, environmental clearances, and a construction estimate.",
      buildOutputs: "Useful outputs: completed facilities, installed equipment, and documented project delivery.",
      operateOutputs: "Useful outputs: operating plan, staffing, maintenance schedule, programming, and performance measures.",
      noPhaseFunding: "No saved funding is assigned to this phase yet.",
      officialEnglish:
        "Official program names, rules, and source material may remain in English. Confirm requirements with the program.",
      plan: "Plan",
      design: "Design",
      build: "Build",
      operate: "Operate",
      dueSoon: "Due soon",
      dueToday: "Due today",
      pastDue: "Past date",
      daysLeft: "{days} days left",
      reviewedDeadline: "Last checked",
      rollingTiming: "Rolling / ongoing",
      recurringTiming: "Recurring cycle / next date pending",
      closedTiming: "Closed / next cycle pending",
      variableTiming: "Deadlines vary by program",
      activePeriodTiming: "Active program period",
      datePendingTiming: "Next deadline not announced",
      compareTitle: "Compare saved options",
      compareLimit: "Choose up to three items to compare.",
      shareReady: "Private share link ready. Project title and notes are not included.",
      shareTooLong: "This selection is too large for a safe share link. Export a workspace file instead.",
      copied: "Link copied.",
      copyFailed: "Select and copy the link.",
      invalidWorkspace: "This workspace file is invalid or unsupported.",
      imported: "Workspace imported.",
      exported: "Workspace exported.",
      deleted: "This roadmap was reset on this device.",
      clearHistoryConfirm: "Reset this roadmap? This removes saved matches, comparison choices, phase assignments, and local notes on this device.",
      stateChanged: "Saved matches were cleared because you selected a different state or territory.",
      stateReset: "Choose a new state or territory to start a fresh plan.",
      clearStateConfirm: "Change state or territory? This clears saved matches, comparisons, phase assignments, and local notes for this browser workspace.",
      phaseChanged: "Moved to {phase}.",
      addedToPlan: "Added to your plan.",
      removedFromPlan: "Removed from your plan.",
      next: "Next",
      back: "Back",
      stepOf: "Step {step} of {total}",
      completePlace: "Choose a state or territory to continue.",
      calendarExported: "Calendar exported.",
      csvExported: "Saved-plan CSV exported.",
      docxExported: "Saved-plan Word document exported.",
      noExportItems: "Save at least one item before exporting a plan.",
      rercieExported: "RERC-e handoff exported.",
      handoffNeedsCommunity: "Add the community name before downloading a plan for RERC-e.",
      handoffMissingSource: "A saved item has no safe official source URL. Remove it or correct the catalog record before exporting.",
      handoffTooLarge: "This plan exceeds the 256 KB RERC-e import limit. Save fewer items or shorten your notes.",
      handoffNextStep: "RERC-e plan file downloaded. RERC-e source or a future reviewed installer can import it: choose Open Community Explorer plan and select the file. The current public 0.4.0 installer cannot import it.",
      openSource: "Open official program page",
      exportWordAction: "Export community plan as Word",
      exportCsvAction: "Export saved plan as CSV",
      saveWorkspaceAction: "Save workspace to a file",
      handoffDownloadAction: "Download plan for RERC-e",
      includeNotes:
        "Include your project notes in the RERC-e handoff? The file stays on this computer unless you share it.",
      installerFallback: "If RERC-e is not installed, download the Windows installer.",
      projectWorkspace: "Community plan",
      communitySnapshot: "Selected location",
      prepared: "Prepared {date}",
      projectNotesHeading: "Project notes",
      selectedItemSummary: "{count} selected item, organized by project phase.",
      selectedItemsSummary: "{count} selected items, organized by project phase.",
      phaseLabel: "{phase} phase",
      overviewHeading: "Overview",
      fundingCategory: "Funding",
      resourceCategory: "Resource",
      caseStudyCategory: "Case study",
      roadmap: "Project roadmap",
      deadlines: "Reviewed deadlines",
      language: "Language",
      english: "English",
      spanish: "Español",
      savedCount: "{count} saved",
      compareCount: "{count} selected",
      unavailable: "Not listed",
      community: "Community",
      geography: "Geography",
      status: "Status",
      applicant: "Eligible applicants",
      stage: "Project stage",
      roadmapPhase: "Your roadmap phase",
      programStage: "Program-supported project stage: {stage}",
      amount: "Amount or cost",
      match: "Match or cost share",
      deadline: "Deadline or availability",
      source: "Official source",
      type: "Type",
      organization: "Organization",
      title: "Title",
      notesExcluded: "Project title and notes are never placed in share links.",
      localOnly: "Saved on this device only.",
      start: "Start",
      matches: "Matches",
      explore: "Explore",
      filters: "Filters",
      myPlan: "My plan",
      choicesPage: "{label}: choices {start}-{end} of {total}",
      applicantChoices: "Applicant choices",
      topicChoices: "Topic choices",
      startupError: "The planner could not start in this browser.",
    },
    es: {
      stateReset: "Elija un nuevo estado o territorio para comenzar un plan nuevo.",
      clearStateConfirm: "Â¿Cambiar el estado o territorio? Esto borra las opciones guardadas, comparaciones, fases y notas locales de este espacio de trabajo.",
      noFundingSequence: "Guarde opciones de financiamiento para crear una estrategia por fases.",
      fundingSequence: "Secuencia de financiamiento",
      fundingSequenceSummary: "{count} opciones guardadas, desde la planificaciÃ³n hasta la operaciÃ³n.",
      fundingSequenceCaveat: "Esta es una secuencia de planificaciÃ³n, no una promesa de fondos. Cada programa toma sus propias decisiones.",
      sequenceStep: "Paso {step}",
      sequenceTiming: "Plazo de solicitud",
      preparesFor: "Puede preparar materiales de solicitud para",
      noLaterTargets: "Prepare el proyecto para la siguiente fase.",
      planPurpose: "Defina el proyecto, los socios, el alcance, el apoyo de la comunidad y los costos iniciales.",
      designPurpose: "Complete el diseÃ±o, la ingenierÃ­a, la revisiÃ³n ambiental, los permisos y costos firmes.",
      buildPurpose: "Financie la construcciÃ³n, adquisiciÃ³n, equipos y otras obras de capital.",
      operatePurpose: "Apoye la programaciÃ³n, el personal, el mantenimiento, la administraciÃ³n y el uso a largo plazo.",
      planOutputs: "Resultados Ãºtiles: plan del proyecto, socios, opiniÃ³n pÃºblica, viabilidad y presupuesto preliminar.",
      designOutputs: "Resultados Ãºtiles: planos, permisos, control del sitio, revisiones ambientales y costo de construcciÃ³n.",
      buildOutputs: "Resultados Ãºtiles: instalaciones terminadas, equipos instalados y entrega documentada.",
      operateOutputs: "Resultados Ãºtiles: plan operativo, personal, mantenimiento, programaciÃ³n y medidas de desempeÃ±o.",
      noPhaseFunding: "TodavÃ­a no hay financiamiento guardado asignado a esta fase.",
      saved: "Guardado",
      save: "Agregar al plan",
      remove: "Quitar del plan",
      compare: "Comparar",
      comparing: "Comparando",
      savedOnly: "Mostrar solo lo guardado",
      savedViewCount: "Se muestran {count} opciones guardadas.",
      savedViewSummary: "Sus opciones guardadas aparecen abajo. Los botones Word y CSV exportan esta vista.",
      savedViewTitle: "Sus opciones guardadas para {state}",
      savedOptionsLabel: "Opciones guardadas",
      allMatchesLabel: "Todas las opciones",
      allMatches: "Mostrar todos los resultados",
      noSaved: "Aún no hay opciones guardadas. Agregue opciones para crear un plan.",
      noDeadlines: "Guarde opciones de financiamiento para ver aquí sus fechas y plazos.",
      officialEnglish:
        "Los nombres, reglas y fuentes oficiales pueden permanecer en inglés. Confirme los requisitos con el programa.",
      plan: "Planificar",
      design: "Diseñar",
      build: "Construir",
      operate: "Operar",
      dueSoon: "Vence pronto",
      dueToday: "Vence hoy",
      pastDue: "Fecha pasada",
      daysLeft: "Quedan {days} días",
      reviewedDeadline: "Última revisión",
      rollingTiming: "Continuo / sin fecha fija",
      recurringTiming: "Ciclo recurrente / próxima fecha pendiente",
      closedTiming: "Cerrado / próximo ciclo pendiente",
      variableTiming: "Las fechas varían según el programa",
      activePeriodTiming: "Período activo del programa",
      datePendingTiming: "Próxima fecha no anunciada",
      compareTitle: "Comparar opciones guardadas",
      compareLimit: "Elija hasta tres elementos para comparar.",
      shareReady: "Enlace privado listo. El título y las notas no están incluidos.",
      shareTooLong: "La selección es demasiado grande para un enlace seguro. Exporte el archivo del espacio de trabajo.",
      copied: "Enlace copiado.",
      copyFailed: "Seleccione y copie el enlace.",
      invalidWorkspace: "El archivo del espacio de trabajo no es válido o compatible.",
      imported: "Espacio de trabajo importado.",
      exported: "Espacio de trabajo exportado.",
      deleted: "Esta ruta se reiniciÃ³ en este dispositivo.",
      clearHistoryConfirm: "Â¿Reiniciar esta ruta? Se eliminarÃ¡n las opciones guardadas, comparaciones, etapas y notas locales de este dispositivo.",
      phaseChanged: "Se moviÃ³ a {phase}.",
      addedToPlan: "Se agregó a su plan.",
      removedFromPlan: "Se quitó de su plan.",
      next: "Siguiente",
      back: "Atrás",
      stepOf: "Paso {step} de {total}",
      completePlace: "Elija un estado o territorio para continuar.",
      calendarExported: "Calendario exportado.",
      csvExported: "CSV del plan exportado.",
      docxExported: "Documento Word del plan exportado.",
      noExportItems: "Guarde al menos un elemento antes de exportar el plan.",
      rercieExported: "Archivo para RERC-e exportado.",
      handoffNeedsCommunity: "Agregue el nombre de la comunidad antes de descargar un plan para RERC-e.",
      handoffMissingSource: "Una opción guardada no tiene una dirección segura de la fuente oficial. Quítela o corrija el registro antes de exportar.",
      handoffTooLarge: "Este plan supera el límite de importación de 256 KB de RERC-e. Guarde menos opciones o acorte sus notas.",
      handoffNextStep: "Archivo del plan de RERC-e descargado. El código fuente de RERC-e o un futuro instalador revisado puede importarlo: elija Abrir plan del explorador comunitario y seleccione el archivo. El instalador público actual 0.4.0 no puede importarlo.",
      openSource: "Abrir la página oficial del programa",
      exportWordAction: "Exportar el plan comunitario a Word",
      exportCsvAction: "Exportar el plan guardado a CSV",
      saveWorkspaceAction: "Guardar el espacio de trabajo en un archivo",
      handoffDownloadAction: "Descargar el plan para RERC-e",
      includeNotes:
        "¿Quiere incluir sus notas del proyecto en el archivo para RERC-e? El archivo permanece en este equipo a menos que lo comparta.",
      installerFallback: "Si RERC-e no está instalado, descargue el instalador para Windows.",
      projectWorkspace: "Plan comunitario",
      communitySnapshot: "Ubicación seleccionada",
      prepared: "Preparado el {date}",
      projectNotesHeading: "Notas del proyecto",
      selectedItemSummary: "{count} elemento seleccionado, organizado por fase del proyecto.",
      selectedItemsSummary: "{count} elementos seleccionados, organizados por fase del proyecto.",
      phaseLabel: "Fase: {phase}",
      overviewHeading: "Resumen",
      fundingCategory: "Financiamiento",
      resourceCategory: "Recurso",
      caseStudyCategory: "Caso práctico",
      roadmap: "Ruta del proyecto",
      deadlines: "Fechas revisadas",
      language: "Idioma",
      english: "English",
      spanish: "Español",
      savedCount: "{count} guardados",
      compareCount: "{count} seleccionados",
      unavailable: "No indicado",
      community: "Comunidad",
      geography: "Geografía",
      status: "Estado",
      applicant: "Solicitantes elegibles",
      stage: "Etapa del proyecto",
      roadmapPhase: "Su fase de planificación",
      programStage: "Etapa del proyecto aceptada por el programa: {stage}",
      amount: "Monto o costo",
      match: "Aporte local",
      deadline: "Fecha o disponibilidad",
      source: "Fuente oficial",
      type: "Tipo",
      organization: "Organización",
      title: "Título",
      notesExcluded: "El título y las notas nunca se incluyen en enlaces compartidos.",
      localOnly: "Guardado solo en este dispositivo.",
      start: "Inicio",
      matches: "Opciones",
      explore: "Explorar",
      filters: "Filtros",
      myPlan: "Mi plan",
      choicesPage: "{label}: opciones {start}-{end} de {total}",
      applicantChoices: "Opciones de solicitante",
      topicChoices: "Opciones de tema",
      startupError: "El planificador no pudo iniciar en este navegador.",
    },
  };

  const state = {
    db: null,
    workspace: null,
    language: "en",
    savedOnly: false,
    wizardStep: 1,
    map: null,
    marker: null,
    saveTimer: null,
    observer: null,
  };
  const dialogOpeners = new WeakMap();

  function explorer() {
    return window.RERCExplorer || {};
  }

  function byId(id) {
    return document.getElementById(id);
  }

  function t(key, variables) {
    let value = (TEXT[state.language] && TEXT[state.language][key]) || TEXT.en[key] || key;
    Object.keys(variables || {}).forEach(function (name) {
      value = value.replace("{" + name + "}", String(variables[name]));
    });
    return value;
  }

  function textValue(value, maxLength) {
    const limit = maxLength || 500;
    return typeof value === "string" ? value.trim().slice(0, limit) : "";
  }

  function catalog() {
    return Array.isArray(explorer().catalog) ? explorer().catalog : [];
  }

  function itemId(item) {
    return textValue(item && (item.item_id || item.id), 160);
  }

  function catalogMap() {
    const map = new Map();
    catalog().forEach(function (item) {
      const id = itemId(item);
      if (id) map.set(id, item);
    });
    return map;
  }

  function uniqueKnownIds(values, maximum) {
    const known = catalogMap();
    const output = [];
    (Array.isArray(values) ? values : []).forEach(function (value) {
      const id = textValue(value, 160);
      if (id && known.has(id) && !output.includes(id) && output.length < maximum) output.push(id);
    });
    return output;
  }

  function defaultWorkspace(id) {
    return {
      schema: SCHEMA_VERSION,
      id: textValue(id, 80) || DEFAULT_WORKSPACE_ID,
      savedIds: [],
      compareIds: [],
      roadmapAssignments: {},
      projectTitle: "",
      projectNotes: "",
      profile: {},
      filters: {},
      updatedAt: new Date().toISOString(),
    };
  }

  function createWorkspaceId() {
    if (window.crypto && typeof window.crypto.randomUUID === "function") {
      return WORKSPACE_ID_PREFIX + window.crypto.randomUUID();
    }
    const random = Math.random().toString(36).slice(2, 14);
    return WORKSPACE_ID_PREFIX + Date.now().toString(36) + "-" + random;
  }

  function activeWorkspaceId() {
    const stored = textValue(localStorage.getItem(LAST_WORKSPACE_KEY), 80);
    if (stored.indexOf(WORKSPACE_ID_PREFIX) === 0) return stored;
    const id = createWorkspaceId();
    localStorage.setItem(LAST_WORKSPACE_KEY, id);
    return id;
  }

  function sanitizeProfile(profile) {
    const source = profile && typeof profile === "object" && !Array.isArray(profile) ? profile : {};
    const output = {};
    const stringFields = [
      "geoid",
      "name",
      "community",
      "state",
      "stateCode",
      "county",
      "placeType",
      "source",
      "vintage",
      "coverageNote",
      "populationLabel",
      "medianIncomeLabel",
      "povertyLabel",
      "broadbandLabel",
    ];
    stringFields.forEach(function (field) {
      const value = textValue(source[field], field === "coverageNote" ? 800 : 240);
      if (value) output[field] = value;
    });
    ["population", "medianHouseholdIncome", "povertyRate", "broadbandRate"].forEach(function (field) {
      const value = Number(source[field]);
      if (Number.isFinite(value)) output[field] = value;
    });
    const latitude = Number(source.latitude);
    const longitude = Number(source.longitude);
    if (Number.isFinite(latitude) && latitude >= -90 && latitude <= 90) output.latitude = latitude;
    if (Number.isFinite(longitude) && longitude >= -180 && longitude <= 180) output.longitude = longitude;
    return output;
  }

  function sanitizeWorkspaceFilters(input, strict) {
    if (input === undefined) return {};
    if (!input || typeof input !== "object" || Array.isArray(input)) throw new Error("workspace-filters");
    const textControls = ["keywordSearch", "stageSelect", "sortSelect", "limitSelect", "caseStudyViewSelect"];
    const choiceRoots = ["applicantOptions", "topicOptions", "fundingTypeOptions", "resourceTypeOptions", "caseStudyPhaseOptions"];
    const allowed = new Set(textControls.concat(choiceRoots, ["includeClosed", "mode"]));
    if (strict && Object.keys(input).some(function (key) { return !allowed.has(key); }))
      throw new Error("workspace-filter-fields");
    const filters = {};
    textControls.forEach(function (id) {
      const value = input[id];
      if (value === undefined) return;
      if (typeof value !== "string" || value.length > (id === "keywordSearch" ? 200 : 100))
        throw new Error("workspace-filter-value");
      const control = byId(id);
      if (id !== "keywordSearch" && control && !Array.from(control.options || []).some(function (option) { return option.value === value; })) {
        if (strict) throw new Error("workspace-filter-option");
        return;
      }
      filters[id] = value;
    });
    choiceRoots.forEach(function (id) {
      if (input[id] === undefined) return;
      if (!Array.isArray(input[id]) || input[id].length > 30 ||
          input[id].some(function (value) { return typeof value !== "string" || value.length > 500; }))
        throw new Error("workspace-filter-choices");
      const root = byId(id);
      const choices = new Set(root ? Array.from(root.querySelectorAll('input[type="checkbox"], input[type="radio"]'))
        .map(function (control) { return control.value; }) : []);
      const selected = input[id].filter(function (value) { return choices.has(value); });
      if (strict && selected.length !== input[id].length) throw new Error("workspace-filter-choice");
      filters[id] = Array.from(new Set(selected));
    });
    if (input.includeClosed !== undefined) {
      if (typeof input.includeClosed !== "boolean") throw new Error("workspace-filter-closed");
      filters.includeClosed = input.includeClosed;
    }
    if (input.mode !== undefined) {
      if (!["All", "Funding", "Resource", "Case Study"].includes(input.mode)) throw new Error("workspace-filter-mode");
      filters.mode = input.mode;
    }
    return filters;
  }

  function sanitizeWorkspace(input, strict) {
    if (!input || typeof input !== "object" || Array.isArray(input)) throw new Error("workspace-object");
    if (Number(input.schema) !== SCHEMA_VERSION) throw new Error("workspace-version");
    const allowed = new Set([
      "schema",
      "id",
      "savedIds",
      "compareIds",
      "roadmapAssignments",
      "projectTitle",
      "projectNotes",
      "profile",
      "filters",
      "updatedAt",
      "catalogVersion",
      "exportedAt",
    ]);
    if (strict && Object.keys(input).some(function (key) { return !allowed.has(key); })) {
      throw new Error("workspace-fields");
    }
    if (!Array.isArray(input.savedIds) || input.savedIds.length > MAX_IDS) throw new Error("workspace-saved");
    if (!Array.isArray(input.compareIds) || input.compareIds.length > MAX_COMPARE) {
      throw new Error("workspace-compare");
    }
    if (typeof input.projectNotes !== "string" || input.projectNotes.length > MAX_NOTES) {
      throw new Error("workspace-notes");
    }
    if (typeof input.projectTitle !== "string" || input.projectTitle.length > 200) {
      throw new Error("workspace-title");
    }
    if (!input.roadmapAssignments || typeof input.roadmapAssignments !== "object" ||
        Array.isArray(input.roadmapAssignments)) {
      throw new Error("workspace-roadmap");
    }

    const savedIds = uniqueKnownIds(input.savedIds, MAX_IDS);
    if (strict && savedIds.length !== input.savedIds.length) throw new Error("workspace-unknown-id");
    const compareIds = uniqueKnownIds(input.compareIds, MAX_COMPARE).filter(function (id) {
      return savedIds.includes(id);
    });
    if (strict && compareIds.length !== input.compareIds.length) throw new Error("workspace-compare-id");
    const assignments = {};
    Object.keys(input.roadmapAssignments).forEach(function (id) {
      const phase = input.roadmapAssignments[id];
      if (savedIds.includes(id) && PHASES.includes(phase)) assignments[id] = phase;
      else if (strict) throw new Error("workspace-roadmap-value");
    });
    return {
      schema: SCHEMA_VERSION,
      id: textValue(input.id, 80) || DEFAULT_WORKSPACE_ID,
      savedIds: savedIds,
      compareIds: compareIds,
      roadmapAssignments: assignments,
      projectTitle: textValue(input.projectTitle, 200),
      projectNotes: input.projectNotes.trim().slice(0, MAX_NOTES),
      profile: sanitizeProfile(input.profile),
      filters: sanitizeWorkspaceFilters(input.filters, strict),
      updatedAt: new Date().toISOString(),
    };
  }

  function openDatabase() {
    return new Promise(function (resolve, reject) {
      if (!window.indexedDB) {
        reject(new Error("indexeddb-unavailable"));
        return;
      }
      const request = indexedDB.open(DB_NAME, DB_VERSION);
      request.onupgradeneeded = function () {
        const db = request.result;
        if (!db.objectStoreNames.contains(WORKSPACE_STORE)) {
          db.createObjectStore(WORKSPACE_STORE, { keyPath: "id" });
        }
      };
      request.onsuccess = function () { resolve(request.result); };
      request.onerror = function () { reject(request.error || new Error("indexeddb-open")); };
    });
  }

  function dbGet(storeName, key) {
    return new Promise(function (resolve, reject) {
      const request = state.db.transaction(storeName, "readonly").objectStore(storeName).get(key);
      request.onsuccess = function () { resolve(request.result || null); };
      request.onerror = function () { reject(request.error || new Error("indexeddb-read")); };
    });
  }

  function dbPut(storeName, value) {
    return new Promise(function (resolve, reject) {
      const request = state.db.transaction(storeName, "readwrite").objectStore(storeName).put(value);
      request.onsuccess = function () { resolve(value); };
      request.onerror = function () { reject(request.error || new Error("indexeddb-write")); };
    });
  }

  function dbClear(storeName) {
    return new Promise(function (resolve, reject) {
      const request = state.db.transaction(storeName, "readwrite").objectStore(storeName).clear();
      request.onsuccess = function () { resolve(); };
      request.onerror = function () { reject(request.error || new Error("indexeddb-clear")); };
    });
  }

  async function persistWorkspace() {
    state.workspace.updatedAt = new Date().toISOString();
    await dbPut(WORKSPACE_STORE, state.workspace);
    localStorage.setItem(LAST_WORKSPACE_KEY, state.workspace.id);
    dispatchUpdate();
  }

  function schedulePersist() {
    window.clearTimeout(state.saveTimer);
    state.saveTimer = window.setTimeout(function () {
      persistWorkspace().catch(reportError);
    }, 250);
  }

  function dispatchUpdate() {
    document.dispatchEvent(new CustomEvent("rerc:workspace-updated", {
      detail: {
        savedCount: state.workspace.savedIds.length,
        compareCount: state.workspace.compareIds.length,
        updatedAt: state.workspace.updatedAt,
      },
    }));
    refreshIcons();
  }

  function refreshIcons() {
    try {
      if (window.lucide && typeof window.lucide.createIcons === "function") {
        window.lucide.createIcons();
      }
    } catch (error) {
      console.warn("RERC planner icon refresh failed.", error);
    }
  }

  function reportError(error) {
    console.error("RERC planner:", error);
  }

  function setStatus(id, message, kind) {
    const element = byId(id);
    if (!element) return;
    element.textContent = message || "";
    element.dataset.status = kind || "info";
  }

  function createButton(label, action, item, active) {
    const button = document.createElement("button");
    button.type = "button";
    button.dataset.action = action;
    button.dataset.itemId = itemId(item);
    button.setAttribute("aria-pressed", active ? "true" : "false");
    button.className = "planner-card-action" + (active ? " active" : "");
    button.textContent = label;
    return button;
  }

  function syncActionButton(button, label, active) {
    const pressed = active ? "true" : "false";
    if (button.getAttribute("aria-pressed") !== pressed) button.setAttribute("aria-pressed", pressed);
    button.classList.toggle("active", active);
    if (button.textContent !== label) button.textContent = label;
  }
  function inferCardItem(card) {
    const known = catalogMap();
    const directId =
      card.dataset.itemId ||
      (card.querySelector("[data-item-id]") && card.querySelector("[data-item-id]").dataset.itemId);
    if (directId && known.has(directId)) return known.get(directId);

    const source = card.querySelector('a[href^="http"]');
    if (source) {
      const href = source.href.replace(/\/$/, "");
      const match = catalog().find(function (item) {
        return textValue(item.source_url, 1000).replace(/\/$/, "") === href;
      });
      if (match) return match;
    }

    const heading = card.querySelector("h2, h3, h4");
    if (heading) {
      const title = heading.textContent.trim();
      return catalog().find(function (item) { return textValue(item.title, 500) === title; }) || null;
    }
    return null;
  }

  function decorateResults() {
    const root = (explorer().elements && explorer().elements.results) || byId("results");
    if (!root || state.savedOnly) return;
    root.querySelectorAll("article, .result-card, [data-result-card]").forEach(function (card) {
      const item = inferCardItem(card);
      if (!item) return;
      const id = itemId(item);
      card.dataset.itemId = id;
      let actions = card.querySelector(".planner-card-actions");
      if (!actions) {
        actions = document.createElement("div");
        actions.className = "planner-card-actions";
        card.appendChild(actions);
      }
      const saved = state.workspace.savedIds.includes(id);
      const compared = state.workspace.compareIds.includes(id);
      let saveButton = actions.querySelector('[data-action="planner-save"]');
      if (!saveButton) {
        saveButton = createButton(saved ? t("remove") : t("save"), "planner-save", item, saved);
        actions.appendChild(saveButton);
      } else {
        syncActionButton(saveButton, saved ? t("remove") : t("save"), saved);
      }
      let compareButton = actions.querySelector('[data-action="planner-compare"]');
      if (!compareButton) {
        compareButton = createButton(compared ? t("comparing") : t("compare"), "planner-compare", item, compared);
        actions.appendChild(compareButton);
      } else {
        syncActionButton(compareButton, compared ? t("comparing") : t("compare"), compared);
      }
    });
  }

  function summaryFor(item) {
    try {
      if (typeof explorer().publicSummary === "function") {
        const value = explorer().publicSummary(item);
        if (typeof value === "string") return value;
        if (value && typeof value.summary === "string") return value.summary;
      }
    } catch (error) {
      reportError(error);
    }
    return textValue(item.summary, 1200);
  }

  function createSavedCard(item, compact) {
    const id = itemId(item);
    const card = document.createElement("article");
    card.className = compact ? "saved-tray-item" : "result-card planner-saved-card";
    card.dataset.itemId = id;

    const heading = document.createElement(compact ? "h4" : "h3");
    heading.textContent = textValue(item.title, 500) || t("unavailable");
    card.appendChild(heading);

    const meta = document.createElement("p");
    meta.className = "result-meta";
    meta.textContent = [
      textValue(item.item_type, 80),
      textValue(item.organization, 300),
      textValue(item.status, 120),
    ].filter(Boolean).join(" · ");
    card.appendChild(meta);

    if (!compact) {
      const summary = document.createElement("p");
      summary.textContent = summaryFor(item);
      card.appendChild(summary);
      const source = safeAnchor(item.source_url, t("openSource"));
      if (source) card.appendChild(source);
    }

    const actions = document.createElement("div");
    actions.className = "planner-card-actions";
    actions.appendChild(createButton(t("remove"), "planner-save", item, true));
    actions.appendChild(createButton(
      state.workspace.compareIds.includes(id) ? t("comparing") : t("compare"),
      "planner-compare",
      item,
      state.workspace.compareIds.includes(id)
    ));
    card.appendChild(actions);
    return card;
  }

  function renderSavedOnly() {
    const root = (explorer().elements && explorer().elements.results) || byId("results");
    if (!root) return;
    root.replaceChildren();
    const items = savedItems();
    const matchElements = explorer().elements || {};
    const counts = {
      matchCount: items.length,
      fundingMatchCount: items.filter(function (item) { return item.item_type === "Funding"; }).length,
      resourceMatchCount: items.filter(function (item) { return item.item_type === "Resource"; }).length,
      caseStudyMatchCount: items.filter(function (item) { return item.item_type === "Case Study"; }).length,
    };
    Object.keys(counts).forEach(function (key) {
      if (matchElements[key]) matchElements[key].textContent = counts[key].toLocaleString();
    });
    if (matchElements.matchCount && matchElements.matchCount.nextElementSibling)
      matchElements.matchCount.nextElementSibling.textContent = t("savedOptionsLabel");
    if (matchElements.matchAnnouncement) matchElements.matchAnnouncement.textContent =
      t("savedViewCount", { count: items.length });
    if (matchElements.communitySummary) matchElements.communitySummary.textContent =
      t("savedViewSummary");
    if (matchElements.communityTitle) matchElements.communityTitle.textContent =
      t("savedViewTitle", { state: state.workspace.profile.state || byId("stateSelect")?.value || "" });
    if (matchElements.nextDeadlinePanel) matchElements.nextDeadlinePanel.hidden = true;
    [matchElements.sortSelect, matchElements.limitSelect].forEach(function (control) {
      if (control && control.closest("label")) control.closest("label").hidden = true;
    });
    if (!items.length) {
      const empty = document.createElement("p");
      empty.className = "empty-state";
      empty.textContent = t("noSaved");
      root.appendChild(empty);
      return;
    }
    items.forEach(function (item) { root.appendChild(createSavedCard(item, false)); });
  }

  function renderSavedTray() {
    const root = byId("savedTrayItems");
    if (!root) return;
    root.replaceChildren();
    const items = savedItems();
    if (!items.length) {
      const empty = document.createElement("p");
      empty.textContent = t("noSaved");
      root.appendChild(empty);
    } else {
      items.forEach(function (item) { root.appendChild(createSavedCard(item, true)); });
    }
    setCount("savedTrayCount", items.length, "savedCount");
  }

  function setCount(id, count, key) {
    const element = byId(id);
    if (!element) return;
    element.textContent = String(count);
    element.setAttribute("aria-label", t(key, { count: count }));
  }

  function savedItems() {
    const known = catalogMap();
    return state.workspace.savedIds.map(function (id) { return known.get(id); }).filter(Boolean);
  }

  async function toggleSaved(id) {
    const index = state.workspace.savedIds.indexOf(id);
    let messageKey = "addedToPlan";
    if (index >= 0) {
      state.workspace.savedIds.splice(index, 1);
      state.workspace.compareIds = state.workspace.compareIds.filter(function (value) { return value !== id; });
      delete state.workspace.roadmapAssignments[id];
      messageKey = "removedFromPlan";
    } else if (state.workspace.savedIds.length < MAX_IDS && catalogMap().has(id)) {
      state.workspace.savedIds.push(id);
      state.workspace.roadmapAssignments[id] = inferPhase(catalogMap().get(id));
    }
    await persistWorkspace();
    refreshWorkspaceUI();
    setStatus("plannerStatus", t(messageKey), "success");
  }

  async function toggleCompare(id) {
    if (!state.workspace.savedIds.includes(id)) {
      if (state.workspace.savedIds.length >= MAX_IDS) return;
      state.workspace.savedIds.push(id);
      state.workspace.roadmapAssignments[id] = inferPhase(catalogMap().get(id));
    }
    const index = state.workspace.compareIds.indexOf(id);
    if (index >= 0) {
      state.workspace.compareIds.splice(index, 1);
    } else if (state.workspace.compareIds.length < MAX_COMPARE) {
      state.workspace.compareIds.push(id);
    } else {
      setStatus("shareStatus", t("compareLimit"), "warning");
      return;
    }
    await persistWorkspace();
    refreshWorkspaceUI();
  }

  function inferPhase(item) {
    const stage = textValue(item && item.project_stage, 300).toLowerCase();
    if (/design|engineering|predevelopment/.test(stage)) return "Design";
    if (/construct|implement|acquisition|capital|build/.test(stage)) return "Build";
    if (/operat|maint|capacity|workforce|business/.test(stage)) return "Operate";
    return "Plan";
  }

  function renderRoadmap() {
    const root = byId("roadmap");
    if (!root) return;
    root.replaceChildren();
    const groups = {};
    PHASES.forEach(function (phase) { groups[phase] = []; });
    savedItems().forEach(function (item) {
      const id = itemId(item);
      const phase = PHASES.includes(state.workspace.roadmapAssignments[id])
        ? state.workspace.roadmapAssignments[id]
        : inferPhase(item);
      groups[phase].push(item);
    });

    PHASES.forEach(function (phase) {
      const section = document.createElement("section");
      section.className = "roadmap-phase";
      const heading = document.createElement("h3");
      heading.textContent = t(phase.toLowerCase());
      section.appendChild(heading);
      if (!groups[phase].length) {
        const empty = document.createElement("p");
        empty.textContent = "0";
        empty.className = "roadmap-empty";
        section.appendChild(empty);
      }
      groups[phase].forEach(function (item) {
        const row = document.createElement("div");
        row.className = "roadmap-item";
        const label = document.createElement("label");
        const selectId = "roadmap-" + cssSafeId(itemId(item));
        label.htmlFor = selectId;
        label.textContent = textValue(item.title, 500);
        const stageLabel = document.createElement("span");
        stageLabel.className = "roadmap-stage-label";
        stageLabel.textContent = t("roadmapPhase");
        const select = document.createElement("select");
        select.id = selectId;
        select.dataset.roadmapId = itemId(item);
        select.setAttribute("aria-label", textValue(item.title, 500) + " " + t("roadmapPhase"));
        PHASES.forEach(function (value) {
          const option = document.createElement("option");
          option.value = value;
          option.textContent = t(value.toLowerCase());
          option.selected = value === phase;
          select.appendChild(option);
        });
        select.value = phase;
        row.append(label, stageLabel, select);
        if (item.project_stage) {
          const programStage = document.createElement("span");
          programStage.className = "roadmap-program-stage";
          programStage.textContent = t("programStage", { stage: textValue(item.project_stage, 300) });
          row.appendChild(programStage);
        }
        section.appendChild(row);
      });
      root.appendChild(section);
    });
    setCount("roadmapCount", state.workspace.savedIds.length, "savedCount");
  }

  function phaseStrategy(phase) {
    const key = phase.toLowerCase();
    return { purpose: t(key + "Purpose"), outputs: t(key + "Outputs") };
  }

  function fundingSequenceEntries() {
    const timingOrder = { dated: 0, rolling: 1, recurring: 2, variable: 3, active_period: 4, date_pending: 5, closed: 6 };
    const entries = savedItems().filter(function (item) {
      return textValue(item.item_type, 80) === "Funding";
    }).map(function (item) {
      const id = itemId(item);
      const phase = PHASES.includes(state.workspace.roadmapAssignments[id])
        ? state.workspace.roadmapAssignments[id] : inferPhase(item);
      return { item: item, phase: phase, deadline: reviewedDeadline(item), timing: fundingTimingInfo(item) };
    }).sort(function (a, b) {
      const phaseDifference = PHASES.indexOf(a.phase) - PHASES.indexOf(b.phase);
      if (phaseDifference) return phaseDifference;
      if (a.deadline && b.deadline) return a.deadline.date.getTime() - b.deadline.date.getTime();
      if (a.deadline) return -1;
      if (b.deadline) return 1;
      return (timingOrder[a.timing.type] ?? 99) - (timingOrder[b.timing.type] ?? 99) ||
        textValue(a.item.title, 500).localeCompare(textValue(b.item.title, 500));
    });
    return entries.map(function (entry, index) { return Object.assign({}, entry, { sequence: index + 1 }); });
  }

  function laterFundingTargets(entries, phase, itemIdValue) {
    const phaseIndex = PHASES.indexOf(phase);
    return entries.filter(function (entry) {
      return itemId(entry.item) !== itemIdValue && PHASES.indexOf(entry.phase) > phaseIndex;
    }).slice(0, 3).map(function (entry) { return textValue(entry.item.title, 500); });
  }

  function sequenceTimingText(entry) {
    if (entry.deadline) {
      return new Intl.DateTimeFormat(state.language, { year: "numeric", month: "short", day: "numeric" }).format(entry.deadline.date);
    }
    return timingLabel(entry.timing.type);
  }

  function renderFundingSequence() {
    const root = byId("fundingSequence");
    if (!root) return;
    root.replaceChildren();
    const entries = fundingSequenceEntries();
    setCount("fundingSequenceCount", entries.length, "savedCount");
    if (!entries.length) {
      const empty = document.createElement("p");
      empty.className = "empty-copy";
      empty.textContent = t("noFundingSequence");
      root.appendChild(empty);
      return;
    }
    const summary = document.createElement("p");
    summary.className = "funding-sequence-summary";
    summary.textContent = t("fundingSequenceSummary", { count: entries.length });
    root.appendChild(summary);
    PHASES.forEach(function (phase, phaseIndex) {
      const strategy = phaseStrategy(phase);
      const phaseEntries = entries.filter(function (entry) { return entry.phase === phase; });
      const section = document.createElement("section");
      section.className = "funding-sequence-phase";
      section.dataset.phase = phase.toLowerCase();
      const header = document.createElement("header");
      const number = document.createElement("span");
      number.className = "funding-phase-number";
      number.textContent = String(phaseIndex + 1);
      const heading = document.createElement("h4");
      heading.textContent = t(phase.toLowerCase());
      header.append(number, heading);
      const purpose = document.createElement("p");
      purpose.className = "funding-phase-purpose";
      purpose.textContent = strategy.purpose;
      const outputs = document.createElement("p");
      outputs.className = "funding-phase-outputs";
      outputs.textContent = strategy.outputs;
      section.append(header, purpose, outputs);
      if (!phaseEntries.length) {
        const empty = document.createElement("p");
        empty.className = "funding-phase-empty";
        empty.textContent = t("noPhaseFunding");
        section.appendChild(empty);
      }
      phaseEntries.forEach(function (entry) {
        const item = entry.item;
        const card = document.createElement("article");
        card.className = "funding-sequence-item";
        const step = document.createElement("span");
        step.className = "funding-sequence-step";
        step.textContent = t("sequenceStep", { step: entry.sequence });
        const title = document.createElement("h5");
        title.textContent = textValue(item.title, 500);
        const timing = document.createElement("p");
        timing.className = "funding-sequence-timing";
        timing.textContent = t("sequenceTiming") + ": " + sequenceTimingText(entry);
        const targets = laterFundingTargets(entries, entry.phase, itemId(item));
        const prepares = document.createElement("p");
        prepares.className = "funding-sequence-prepares";
        prepares.textContent = targets.length ? t("preparesFor") + ": " + targets.join("; ") : t("noLaterTargets");
        card.append(step, title, timing, prepares);
        section.appendChild(card);
      });
      root.appendChild(section);
    });
    const caveat = document.createElement("p");
    caveat.className = "funding-sequence-caveat";
    caveat.textContent = t("fundingSequenceCaveat");
    root.appendChild(caveat);
  }

  function cssSafeId(value) {
    return String(value).replace(/[^A-Za-z0-9_-]/g, "-").slice(0, 100);
  }

  function reviewedDeadline(item) {
    if (typeof explorer().parseDeadline !== "function") return null;
    try {
      const parsed = explorer().parseDeadline(item);
      if (!parsed || typeof parsed !== "object") return null;
      if (parsed instanceof Date) {
        if (Number.isNaN(parsed.getTime())) return null;
        return {
          date: parsed,
          kind: "reviewed",
          source: textValue(item.source_url, 1000),
          reviewedAt: textValue(item.last_checked, 80),
        };
      }
      const reviewed =
        parsed.reviewed === true ||
        parsed.isReviewed === true ||
        parsed.status === "reviewed" ||
        parsed.confidence === "reviewed";
      if (!reviewed) return null;
      const candidate = parsed.date || parsed.closesOn || parsed.closes_on || parsed.iso || parsed.value;
      const date = candidate instanceof Date ? candidate : new Date(candidate);
      if (Number.isNaN(date.getTime())) return null;
      return {
        date: date,
        kind: textValue(parsed.kind || parsed.deadlineKind, 80),
        source: textValue(parsed.source || item.source_url, 1000),
        reviewedAt: textValue(parsed.reviewedAt || parsed.reviewed_at || item.last_checked, 80),
      };
    } catch (error) {
      reportError(error);
      return null;
    }
  }

  function deadlineLabel(date) {
    const today = new Date();
    const start = new Date(today.getFullYear(), today.getMonth(), today.getDate());
    const due = new Date(date.getFullYear(), date.getMonth(), date.getDate());
    const days = Math.round((due.getTime() - start.getTime()) / 86400000);
    if (days < 0) return { text: t("pastDue"), kind: "past" };
    if (days === 0) return { text: t("dueToday"), kind: "urgent" };
    if (days <= 30) return { text: t("dueSoon") + ": " + t("daysLeft", { days: days }), kind: "soon" };
    return { text: t("daysLeft", { days: days }), kind: "future" };
  }

  function fundingTimingInfo(item) {
    if (typeof explorer().fundingTiming === "function") return explorer().fundingTiming(item);
    return {
      type: "date_pending",
      label: t("datePendingTiming"),
      detail: textValue(item.deadline_or_availability, 1000) || "Check the official program page.",
      date: null,
    };
  }

  function timingLabel(type) {
    const keys = {
      rolling: "rollingTiming",
      recurring: "recurringTiming",
      closed: "closedTiming",
      variable: "variableTiming",
      active_period: "activePeriodTiming",
      date_pending: "datePendingTiming",
    };
    return t(keys[type] || "datePendingTiming");
  }

  function checkedDateLabel(value) {
    const raw = textValue(value, 80);
    const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(raw);
    if (!match) return raw;
    const date = new Date(Number(match[1]), Number(match[2]) - 1, Number(match[3]));
    return new Intl.DateTimeFormat(state.language, { year: "numeric", month: "short", day: "numeric" }).format(date);
  }

  function deadlineItems() {
    const order = { dated: 0, rolling: 1, recurring: 2, variable: 3, active_period: 4, date_pending: 5, closed: 6 };
    return savedItems().filter(function (item) {
      return textValue(item.item_type, 80) === "Funding";
    }).map(function (item) {
      return { item: item, deadline: reviewedDeadline(item), timing: fundingTimingInfo(item) };
    }).sort(function (a, b) {
      if (a.deadline && b.deadline) return a.deadline.date.getTime() - b.deadline.date.getTime();
      if (a.deadline) return -1;
      if (b.deadline) return 1;
      return (order[a.timing.type] ?? 99) - (order[b.timing.type] ?? 99) || textValue(a.item.title, 500).localeCompare(textValue(b.item.title, 500));
    });
  }

  function renderDeadlines() {
    const root = byId("deadlineList");
    if (!root) return;
    root.replaceChildren();
    const deadlines = deadlineItems();
    if (!deadlines.length) {
      const empty = document.createElement("p");
      empty.className = "empty-copy";
      empty.textContent = t("noDeadlines");
      root.appendChild(empty);
      return;
    }
    deadlines.forEach(function (entry) {
      const row = document.createElement("article");
      row.className = "deadline-item";
      const heading = document.createElement("h3");
      heading.textContent = textValue(entry.item.title, 500);
      const main = document.createElement("div");
      main.className = "deadline-main";
      if (entry.deadline) {
        const date = document.createElement("time");
        date.dateTime = isoDate(entry.deadline.date);
        date.textContent = new Intl.DateTimeFormat(state.language, {
          year: "numeric",
          month: "long",
          day: "numeric",
        }).format(entry.deadline.date);
        const badge = document.createElement("span");
        const label = deadlineLabel(entry.deadline.date);
        badge.className = "deadline-label " + label.kind;
        badge.textContent = label.text;
        main.append(date, badge);
      } else {
        const status = document.createElement("span");
        status.className = "deadline-status " + entry.timing.type;
        status.textContent = timingLabel(entry.timing.type);
        main.appendChild(status);
      }
      const detail = document.createElement("p");
      detail.className = "deadline-detail";
      detail.textContent = textValue(entry.timing.detail || entry.item.deadline_or_availability, 1000);
      const footer = document.createElement("div");
      footer.className = "deadline-footer";
      const reviewed = document.createElement("small");
      reviewed.textContent = [t("reviewedDeadline"), checkedDateLabel(entry.deadline?.reviewedAt || entry.item.last_checked)].filter(Boolean).join(": ");
      footer.appendChild(reviewed);
      const source = typeof explorer().safeUrl === "function" ? explorer().safeUrl(entry.item.source_url) : "";
      if (source) {
        const link = document.createElement("a");
        link.href = source;
        link.target = "_blank";
        link.rel = "noopener";
        link.textContent = t("openSource");
        footer.appendChild(link);
      }
      row.append(heading, main, detail, footer);
      root.appendChild(row);
    });
  }

  function renderComparison() {
    const tableRoot = byId("comparisonTable");
    if (!tableRoot) return;
    tableRoot.replaceChildren();
    const known = catalogMap();
    const items = state.workspace.compareIds.map(function (id) { return known.get(id); }).filter(Boolean);
    if (!items.length) {
      const empty = document.createElement("p");
      empty.textContent = t("compareLimit");
      tableRoot.appendChild(empty);
      return;
    }
    const table = document.createElement("table");
    const caption = document.createElement("caption");
    caption.textContent = t("compareTitle");
    table.appendChild(caption);
    const head = document.createElement("thead");
    const headRow = document.createElement("tr");
    const emptyHead = document.createElement("th");
    emptyHead.scope = "col";
    headRow.appendChild(emptyHead);
    items.forEach(function (item) {
      const th = document.createElement("th");
      th.scope = "col";
      th.textContent = textValue(item.title, 500);
      headRow.appendChild(th);
    });
    head.appendChild(headRow);
    table.appendChild(head);
    const body = document.createElement("tbody");
    [
      ["type", "item_type"],
      ["organization", "organization"],
      ["status", "status"],
      ["geography", "geography"],
      ["applicant", "eligible_users"],
      ["stage", "project_stage"],
      ["amount", "amount_or_cost"],
      ["match", "match_or_cost"],
      ["deadline", "deadline_or_availability"],
    ].forEach(function (definition) {
      const row = document.createElement("tr");
      const label = document.createElement("th");
      label.scope = "row";
      label.textContent = t(definition[0]);
      row.appendChild(label);
      items.forEach(function (item) {
        const cell = document.createElement("td");
        cell.textContent = textValue(item[definition[1]], 2000) || t("unavailable");
        row.appendChild(cell);
      });
      body.appendChild(row);
    });
    table.appendChild(body);
    tableRoot.appendChild(table);
  }

  function refreshCounts() {
    const saved = state.workspace.savedIds.length;
    const compared = state.workspace.compareIds.length;
    ["savedCountBadge", "mobileSavedCount", "savedTrayCount"].forEach(function (id) {
      setCount(id, saved, "savedCount");
    });
    ["compareCountBadge"].forEach(function (id) {
      setCount(id, compared, "compareCount");
    });
    const openCompare = byId("openCompare");
    if (openCompare) openCompare.disabled = compared === 0;
    const compareSaved = byId("compareSaved");
    if (compareSaved) compareSaved.disabled = compared === 0;
  }

  function refreshWorkspaceUI() {
    refreshCounts();
    renderSavedTray();
    renderRoadmap();
    renderFundingSequence();
    renderDeadlines();
    renderComparison();
    if (state.savedOnly) renderSavedOnly();
    else decorateResults();
    syncSavedOnlyControl();
    refreshIcons();
  }

  function syncSavedOnlyControl() {
    const control = byId("showSavedOnly");
    if (!control) return;
    if ("checked" in control) control.checked = state.savedOnly;
    control.setAttribute("aria-pressed", state.savedOnly ? "true" : "false");
    if (control.tagName === "BUTTON") {
      const label = control.querySelector(".saved-only-label");
      if (label) label.textContent = state.savedOnly ? t("allMatches") : t("savedOnly");
    }
  }

  function toggleSavedOnly(force) {
    state.savedOnly = typeof force === "boolean" ? force : !state.savedOnly;
    if (state.savedOnly) {
      renderSavedOnly();
    } else if (typeof explorer().render === "function") {
      const deadlinePanel = explorer().elements && explorer().elements.nextDeadlinePanel;
      if (deadlinePanel) deadlinePanel.hidden = false;
      [explorer().elements && explorer().elements.sortSelect,
        explorer().elements && explorer().elements.limitSelect].forEach(function (control) {
        if (control && control.closest("label")) control.closest("label").hidden = false;
      });
      const matchCount = explorer().elements && explorer().elements.matchCount;
      if (matchCount && matchCount.nextElementSibling)
        matchCount.nextElementSibling.textContent = t("allMatchesLabel");
      explorer().render();
      window.requestAnimationFrame(decorateResults);
    }
    syncSavedOnlyControl();
  }

  function openDialog(id) {
    const dialog = byId(id);
    if (!dialog) return;
    const opener = document.activeElement;
    if (opener instanceof HTMLElement && !dialog.contains(opener)) dialogOpeners.set(dialog, opener);
    if (typeof dialog.showModal === "function") dialog.showModal();
    else {
      dialog.hidden = false;
      dialog.setAttribute("open", "");
    }
    const focusable = dialog.querySelector("button, input, select, textarea, a[href]");
    if (focusable) focusable.focus();
  }

  function closeDialog(dialog) {
    if (!dialog) return;
    if (typeof dialog.close === "function") dialog.close();
    else {
      dialog.hidden = true;
      dialog.removeAttribute("open");
    }
    const opener = dialogOpeners.get(dialog);
    dialogOpeners.delete(dialog);
    if (opener && opener.isConnected) window.requestAnimationFrame(function () { opener.focus(); });
  }

  function revealCommunityForm(focusMissing) {
    const filters = byId("communityFilters");
    const toggle = byId("toggleFilters");
    if (filters) {
      filters.hidden = false;
      filters.classList.add("open");
      filters.scrollIntoView({ behavior: "smooth", block: "start" });
    }
    if (toggle) {
      toggle.setAttribute("aria-expanded", "true");
      const label = toggle.querySelector("span");
      if (label) label.textContent = "Hide questions";
    }
    if (typeof state.showWizardStep === "function") state.showWizardStep(1, { focus: false });
    if (focusMissing) {
      const stateSelect = byId("stateSelect");
      const target = stateSelect;
      if (target) window.requestAnimationFrame(function () { target.focus({ preventScroll: true }); });
    }
  }

  function syncCommunityGate() {
    const ready = hasPlaceSelection();
    document.documentElement.classList.toggle("community-ready", ready);
    document.querySelectorAll("[data-community-gated]").forEach(function (section) {
      section.hidden = !ready;
      section.setAttribute("aria-hidden", ready ? "false" : "true");
    });
    document.querySelectorAll("#workflowSteps [data-wizard-step]").forEach(function (button) {
      const step = Number(button.dataset.wizardStep || 1);
      button.disabled = !ready && step > 1;
      button.setAttribute("aria-disabled", button.disabled ? "true" : "false");
    });
    if (ready) {
      const stateSelect = byId("stateSelect");
      [stateSelect].forEach(function (control) {
        if (!control) return;
        control.setCustomValidity("");
        control.removeAttribute("aria-invalid");
      });
    }
    return ready;
  }

  function requireCommunityInfo() {
    if (syncCommunityGate()) return true;
    const stateSelect = byId("stateSelect");
    const message = t("completePlace");
    const controls = [stateSelect];
    controls.forEach(function (control) {
      if (!control) return;
      const missing = !control.value;
      control.setCustomValidity(missing ? message : "");
      if (missing) control.setAttribute("aria-invalid", "true");
      else control.removeAttribute("aria-invalid");
    });
    setStatus("profileStatus", message, "warning");
    revealCommunityForm(true);
    const firstMissing = controls.find(function (control) { return control && !control.value; });
    if (firstMissing && typeof firstMissing.reportValidity === "function") firstMissing.reportValidity();
    return false;
  }
  function setupWizard() {
    const root = byId("workflowSteps");
    const form = byId("communityFilters");
    if (!root || !form) return;
    const stepButtons = Array.from(root.querySelectorAll("[data-wizard-step], [data-step]"));
    const panels = Array.from(document.querySelectorAll("[data-wizard-panel]"));
    const total = Math.max(stepButtons.length, 4);
    let controls = form.querySelector(".wizard-controls");
    if (!controls) {
      controls = document.createElement("div");
      controls.className = "wizard-controls";
      const back = document.createElement("button");
      back.type = "button";
      back.dataset.wizardBack = "";
      back.textContent = t("back");
      const next = document.createElement("button");
      next.type = "button";
      next.dataset.wizardNext = "";
      next.textContent = t("next");
      controls.append(back, next);
      form.appendChild(controls);
    }

    function showStep(nextStep, options) {
      const requested = Math.min(Math.max(Number(nextStep) || 1, 1), total);
      if (requested > 1 && !requireCommunityInfo()) return false;
      state.wizardStep = requested;
      stepButtons.forEach(function (button, index) {
        const step = Number(button.dataset.wizardStep || button.dataset.step || index + 1);
        const active = step === state.wizardStep;
        button.setAttribute("aria-current", active ? "step" : "false");
        button.classList.toggle("active", active);
      });
      panels.forEach(function (panel, index) {
        const step = Number(panel.dataset.wizardPanel || index + 1);
        panel.hidden = step !== state.wizardStep;
      });
      form.hidden = state.wizardStep >= 3;
      root.setAttribute("aria-label", t("stepOf", { step: state.wizardStep, total: total }));
      root.dataset.currentStep = String(state.wizardStep);
      const back = controls.querySelector("[data-wizard-back]");
      const next = controls.querySelector("[data-wizard-next]");
      if (back) back.hidden = state.wizardStep <= 1;
      if (next) next.hidden = state.wizardStep >= 3;
      if (state.wizardStep >= 3) {
        captureProfileFromFilters();
        if (typeof explorer().render === "function") explorer().render();
        const destination = byId(state.wizardStep === 4 ? "planWorkspace" : "matchesWorkspace");
        if (destination) {
          destination.hidden = false;
          destination.setAttribute("aria-hidden", "false");
          destination.scrollIntoView({ behavior: "smooth", block: "start" });
          if (!options || options.focus !== false) destination.focus({ preventScroll: true });
        }
      }
      syncCommunityGate();
      return true;
    }

    function handleNavigation(event) {
      const target = event.target.closest("[data-wizard-step], [data-step], [data-wizard-next], [data-wizard-back]");
      if (!target) return;
      event.preventDefault();
      if (target.hasAttribute("data-wizard-next")) showStep(state.wizardStep + 1);
      else if (target.hasAttribute("data-wizard-back")) showStep(state.wizardStep - 1);
      else showStep(target.dataset.wizardStep || target.dataset.step);
    }

    root.addEventListener("click", handleNavigation);
    form.addEventListener("click", handleNavigation);
    state.showWizardStep = showStep;
    showStep(1, { focus: false });
  }

  function choiceItems(root) {
    return Array.from(root.children).filter(function (child) {
      return child.matches("label, .check-option, .choice-option") ||
        Boolean(child.querySelector('input[type="checkbox"], input[type="radio"]'));
    });
  }

  function setupChoicePager(rootId, labelKey) {
    const root = byId(rootId);
    if (!root || root.dataset.choicePagerReady === "true") return;
    const choices = choiceItems(root);
    if (choices.length <= 6) return;
    root.dataset.choicePagerReady = "true";
    root.dataset.choicePage = "0";
    root.dataset.choiceLabelKey = labelKey;

    const status = document.createElement("p");
    status.className = "choice-pager-status";
    status.setAttribute("aria-live", "polite");
    const controls = document.createElement("div");
    controls.className = "choice-pager-controls";
    const back = document.createElement("button");
    back.type = "button";
    back.dataset.choiceBack = rootId;
    back.textContent = t("back");
    back.setAttribute("aria-label", t("back") + ": " + t(labelKey));
    const next = document.createElement("button");
    next.type = "button";
    next.dataset.choiceNext = rootId;
    next.textContent = t("next");
    next.setAttribute("aria-label", t("next") + ": " + t(labelKey));
    controls.append(back, status, next);
    root.after(controls);

    function showPage(page) {
      const totalPages = Math.ceil(choices.length / 6);
      const current = Math.min(Math.max(Number(page) || 0, 0), totalPages - 1);
      const start = current * 6;
      const end = Math.min(start + 6, choices.length);
      root.dataset.choicePage = String(current);
      choices.forEach(function (choice, index) {
        choice.hidden = index < start || index >= end;
      });
      back.disabled = current === 0;
      next.disabled = current === totalPages - 1;
      status.textContent = t("choicesPage", {
        label: t(labelKey),
        start: start + 1,
        end: end,
        total: choices.length,
      });
    }

    controls.addEventListener("click", function (event) {
      const button = event.target.closest("button");
      if (!button) return;
      const current = Number(root.dataset.choicePage || 0);
      showPage(button.hasAttribute("data-choice-back") ? current - 1 : current + 1);
      const visibleChoice = choices.find(function (choice) { return !choice.hidden; });
      const focusable = visibleChoice && visibleChoice.querySelector("input, button");
      if (focusable) focusable.focus();
    });
    showPage(0);
  }

  function mobileNavItem(label, icon, target, buttonAction) {
    const element = buttonAction ? document.createElement("button") : document.createElement("a");
    if (buttonAction) {
      element.type = "button";
      element.dataset.mobileAction = buttonAction;
    } else {
      element.href = target;
    }
    const iconElement = document.createElement("i");
    iconElement.dataset.lucide = icon;
    iconElement.setAttribute("aria-hidden", "true");
    const text = document.createElement("span");
    text.textContent = label;
    element.append(iconElement, text);
    return element;
  }

  function setupMobileNavigation() {
    let nav = byId("plannerMobileNav") || document.querySelector(".mobile-nav");
    if (!nav) {
      nav = document.createElement("nav");
      nav.id = "plannerMobileNav";
      const explore = mobileNavItem(t("explore"), "search", "", "explore");
      explore.dataset.labelKey = "explore";
      const filters = mobileNavItem(t("filters"), "sliders-horizontal", "", "filters");
      filters.dataset.labelKey = "filters";
      const saved = mobileNavItem(t("saved"), "bookmark", "", "saved");
      saved.dataset.labelKey = "saved";
      const badge = document.createElement("span");
      badge.id = "mobileSavedCount";
      badge.className = "mobile-nav-badge";
      badge.textContent = String(state.workspace.savedIds.length);
      badge.setAttribute("aria-label", t("savedCount", { count: state.workspace.savedIds.length }));
      saved.appendChild(badge);
      const plan = mobileNavItem(t("myPlan"), "clipboard-list", "", "plan");
      plan.dataset.labelKey = "myPlan";
      nav.append(explore, filters, saved, plan);
      document.body.appendChild(nav);
    } else {
      nav.id = "plannerMobileNav";
      nav.querySelectorAll("a, button").forEach(function (item) {
        const href = item.getAttribute("href") || "";
        if (item.dataset.mobileAction === "saved") item.dataset.labelKey = "saved";
        else if (href === "#communityFilters") { item.dataset.labelKey = "start"; item.dataset.mobileAction = "filters"; }
        else if (href === "#matchesWorkspace") { item.dataset.labelKey = "matches"; item.dataset.mobileAction = "explore"; }
        else if (href === "#planWorkspace") { item.dataset.labelKey = "myPlan"; item.dataset.mobileAction = "plan"; }
      });
    }
    nav.setAttribute("aria-label", t("projectWorkspace"));
    if (nav.dataset.plannerBound === "true") return;
    nav.dataset.plannerBound = "true";
    nav.addEventListener("click", function (event) {
      const action = event.target.closest("[data-mobile-action]");
      if (!action) return;
      const mobileAction = action.dataset.mobileAction;
      if (mobileAction === "filters") {
        event.preventDefault();
        revealCommunityForm(true);
        return;
      }
      if (mobileAction === "explore" || mobileAction === "plan") {
        event.preventDefault();
        if (!requireCommunityInfo()) return;
        if (typeof state.showWizardStep === "function") state.showWizardStep(mobileAction === "plan" ? 4 : 3);
        return;
      }
      if (mobileAction === "saved") {
        const tray = byId("savedTray");
        const toggle = byId("toggleSavedTray");
        if (tray) tray.hidden = false;
        if (toggle) toggle.setAttribute("aria-expanded", "true");
        renderSavedTray();
        if (tray) {
          tray.scrollIntoView({ behavior: "smooth", block: "start" });
          const firstAction = tray.querySelector("button, a");
          if (firstAction) firstAction.focus({ preventScroll: true });
        }
      }
    });
  }
  function hasPlaceSelection() {
    const stateSelect = byId("stateSelect");
    return Boolean(stateSelect && stateSelect.value);
  }

  function selectedValues(root) {
    if (!root) return [];
    return Array.from(root.querySelectorAll('input[type="checkbox"]:checked, input[type="radio"]:checked'))
      .map(function (input) { return input.value; })
      .filter(Boolean);
  }

  function controlledFilters() {
    const values = {};
    ["stateSelect", "stageSelect", "sortSelect", "limitSelect"].forEach(function (id) {
      const element = byId(id);
      if (element && element.value) values[id] = textValue(element.value, 100);
    });
    ["applicantOptions", "topicOptions"].forEach(function (id) {
      const selected = selectedValues(byId(id)).map(function (value) { return textValue(value, 100); }).slice(0, 30);
      if (selected.length) values[id] = selected;
    });
    const includeClosed = byId("includeClosed");
    if (includeClosed) values.includeClosed = Boolean(includeClosed.checked);
    const modeButton = document.querySelector("[data-mode][aria-pressed='true']");
    if (modeButton) values.mode = textValue(modeButton.dataset.mode, 40);
    return values;
  }

  function captureWorkspaceFilters() {
    const filters = {};
    ["keywordSearch", "stageSelect", "sortSelect", "limitSelect", "caseStudyViewSelect"].forEach(function (id) {
      const control = byId(id);
      if (control) filters[id] = textValue(control.value, id === "keywordSearch" ? 200 : 100);
    });
    ["applicantOptions", "topicOptions", "fundingTypeOptions", "resourceTypeOptions", "caseStudyPhaseOptions"].forEach(function (id) {
      filters[id] = selectedValues(byId(id)).map(function (value) { return textValue(value, 500); }).slice(0, 30);
    });
    const includeClosed = byId("includeClosed");
    filters.includeClosed = Boolean(includeClosed && includeClosed.checked);
    filters.mode = typeof explorer().getMode === "function" ? explorer().getMode() : "All";
    state.workspace.filters = sanitizeWorkspaceFilters(filters, true);
    schedulePersist();
  }

  function applyWorkspaceFilters() {
    const filters = state.workspace.filters || {};
    if (!Object.keys(filters).length) return;
    ["keywordSearch", "stageSelect", "sortSelect", "limitSelect", "caseStudyViewSelect"].forEach(function (id) {
      const control = byId(id);
      if (control && Object.prototype.hasOwnProperty.call(filters, id)) control.value = filters[id];
    });
    ["applicantOptions", "topicOptions", "fundingTypeOptions", "resourceTypeOptions", "caseStudyPhaseOptions"].forEach(function (id) {
      const root = byId(id);
      if (!root || !Array.isArray(filters[id])) return;
      root.querySelectorAll('input[type="checkbox"], input[type="radio"]').forEach(function (control) {
        control.checked = filters[id].includes(control.value);
      });
    });
    const includeClosed = byId("includeClosed");
    if (includeClosed && typeof filters.includeClosed === "boolean") includeClosed.checked = filters.includeClosed;
    if (filters.mode && typeof explorer().chooseMode === "function") explorer().chooseMode(filters.mode);
    else if (typeof explorer().render === "function") explorer().render();
  }

  function applyControlledFilters(filters) {
    if (!filters || typeof filters !== "object") return;
    ["stateSelect", "stageSelect", "sortSelect", "limitSelect"].forEach(function (id) {
      const element = byId(id);
      const value = textValue(filters[id], 100);
      if (element && value && Array.from(element.options || []).some(function (option) { return option.value === value; })) {
        element.value = value;
      }
    });
    ["applicantOptions", "topicOptions"].forEach(function (id) {
      const allowed = Array.isArray(filters[id]) ? filters[id].map(String) : [];
      const root = byId(id);
      if (root) {
        root.querySelectorAll('input[type="checkbox"], input[type="radio"]').forEach(function (input) {
          input.checked = allowed.includes(input.value);
        });
      }
    });
    const includeClosed = byId("includeClosed");
    if (includeClosed && typeof filters.includeClosed === "boolean") includeClosed.checked = filters.includeClosed;
    if (filters.mode && typeof explorer().chooseMode === "function") {
      explorer().chooseMode(textValue(filters.mode, 40));
    }
  }

  function captureProfileFromFilters() {
    const stateSelect = byId("stateSelect");
    const community = textValue(byId("projectCommunity") && byId("projectCommunity").value, 200);
    const profile = {};
    if (stateSelect && stateSelect.value) {
      profile.state = stateSelect.options[stateSelect.selectedIndex]
        ? stateSelect.options[stateSelect.selectedIndex].text.trim().slice(0, 120)
        : stateSelect.value.slice(0, 120);
      profile.stateCode = stateSelect.value.slice(0, 120);
      if (community) profile.community = community;
      profile.name = community || profile.state;
      profile.placeType = "state_or_territory";
    }
    state.workspace.profile = sanitizeProfile(profile);
    schedulePersist();
  }
  function profileRows(profile) {
    if (!profile || !profile.state) return [];
    return [{ label: t("geography"), value: String(profile.state) }];
  }
  function safeHttpUrl(value) {
    try {
      if (typeof explorer().safeUrl === "function") {
        const checked = explorer().safeUrl(value);
        if (!checked) return "";
        value = checked;
      }
      const url = new URL(String(value), window.location.href);
      return url.protocol === "https:" || url.protocol === "http:" ? url.href : "";
    } catch (error) {
      return "";
    }
  }

  function safeAnchor(url, label) {
    const checked = safeHttpUrl(url);
    if (!checked) return null;
    const anchor = document.createElement("a");
    anchor.href = checked;
    anchor.target = "_blank";
    anchor.rel = "noopener noreferrer";
    anchor.referrerPolicy = "no-referrer";
    anchor.textContent = label;
    return anchor;
  }

  function shareProfile() {
    const profile = state.workspace.profile;
    const output = {};
    ["geoid", "state", "stateCode", "county", "placeType"].forEach(function (field) {
      const value = textValue(profile[field], 120);
      if (value) output[field] = value;
    });
    if (Number.isFinite(profile.latitude)) output.latitude = Number(profile.latitude.toFixed(5));
    if (Number.isFinite(profile.longitude)) output.longitude = Number(profile.longitude.toFixed(5));
    return output;
  }

  function compactId(id) {
    const index = catalog().findIndex(function (item) { return itemId(item) === id; });
    return index >= 0 ? index.toString(36) : "";
  }

  function expandCompactId(token) {
    if (typeof token !== "string" || !/^[0-9a-z]+$/.test(token)) return "";
    const index = parseInt(token, 36);
    return catalog()[index] ? itemId(catalog()[index]) : "";
  }

  function encodeSharePayload(payload) {
    const bytes = new TextEncoder().encode(JSON.stringify(payload));
    let binary = "";
    bytes.forEach(function (byte) { binary += String.fromCharCode(byte); });
    return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
  }

  function decodeSharePayload(value) {
    const normalized = value.replace(/-/g, "+").replace(/_/g, "/");
    const padded = normalized + "=".repeat((4 - normalized.length % 4) % 4);
    const binary = atob(padded);
    const bytes = Uint8Array.from(binary, function (character) { return character.charCodeAt(0); });
    return JSON.parse(new TextDecoder().decode(bytes));
  }

  function createShareLink() {
    const payload = {
      v: SCHEMA_VERSION,
      s: state.workspace.savedIds.map(compactId).filter(Boolean),
      c: state.workspace.compareIds.map(compactId).filter(Boolean),
      f: controlledFilters(),
      l: state.language,
      g: shareProfile(),
    };
    const url = new URL(window.location.href);
    url.hash = "s=" + encodeSharePayload(payload);
    if (url.href.length > MAX_SHARE_LENGTH) throw new Error("share-length");
    return url.href;
  }

  function validateSharePayload(payload) {
    if (!payload || typeof payload !== "object" || Array.isArray(payload) || payload.v !== SCHEMA_VERSION) {
      throw new Error("share-schema");
    }
    const savedTokens = Array.isArray(payload.s) ? payload.s.slice(0, MAX_IDS) : [];
    const compareTokens = Array.isArray(payload.c) ? payload.c.slice(0, MAX_COMPARE) : [];
    const savedIds = uniqueKnownIds(savedTokens.map(expandCompactId), MAX_IDS);
    const compareIds = uniqueKnownIds(compareTokens.map(expandCompactId), MAX_COMPARE)
      .filter(function (id) { return savedIds.includes(id); });
    const filters = payload.f && typeof payload.f === "object" && !Array.isArray(payload.f) ? payload.f : {};
    const language = ALLOWED_LANGUAGES.includes(payload.l) ? payload.l : "en";
    return {
      savedIds: savedIds,
      compareIds: compareIds,
      filters: filters,
      language: language,
      profile: sanitizeProfile(payload.g),
    };
  }

  async function importShareFromHash() {
    if (!window.location.hash.startsWith("#s=") || window.location.href.length > MAX_SHARE_LENGTH) return;
    try {
      const shared = validateSharePayload(decodeSharePayload(window.location.hash.slice(3)));
      state.workspace.savedIds = shared.savedIds;
      state.workspace.compareIds = shared.compareIds;
      state.workspace.profile = shared.profile;
      shared.savedIds.forEach(function (id) {
        if (!state.workspace.roadmapAssignments[id]) {
          state.workspace.roadmapAssignments[id] = inferPhase(catalogMap().get(id));
        }
      });
      state.language = shared.language;
      localStorage.setItem(LANGUAGE_KEY, state.language);
      applyControlledFilters(shared.filters);
      await persistWorkspace();
    } catch (error) {
      setStatus("shareStatus", t("invalidWorkspace"), "error");
      reportError(error);
    }
  }

  function showShareDialog() {
    const input = byId("shareLink");
    try {
      const link = createShareLink();
      if (input) {
        input.value = link;
        input.readOnly = true;
      }
      setStatus("shareStatus", t("shareReady") + " " + t("notesExcluded"), "success");
      openDialog("shareDialog");
    } catch (error) {
      setStatus("shareStatus", t("shareTooLong"), "warning");
      openDialog("shareDialog");
    }
  }

  async function copyShareLink() {
    const input = byId("shareLink");
    if (!input || !input.value) return;
    try {
      await navigator.clipboard.writeText(input.value);
      setStatus("shareStatus", t("copied"), "success");
    } catch (error) {
      input.focus();
      input.select();
      setStatus("shareStatus", t("copyFailed"), "warning");
    }
  }

  async function exportWorkspace() {
    captureWorkspaceFilters();
    window.clearTimeout(state.saveTimer);
    try { await persistWorkspace(); } catch (error) { reportError(error); }
    const payload = Object.assign({}, state.workspace, {
      schema: SCHEMA_VERSION,
      catalogVersion: catalogVersion(),
      exportedAt: new Date().toISOString(),
    });
    downloadBlob(
      new Blob([JSON.stringify(payload, null, 2)], { type: "application/json;charset=utf-8" }),
      fileStem() + ".rerc-workspace"
    );
    setStatus("shareStatus", t("exported"), "success");
  }

  async function importWorkspace(file) {
    if (!file || file.size > MAX_FILE_BYTES) throw new Error("workspace-size");
    const text = await file.text();
    if (new Blob([text]).size > MAX_FILE_BYTES) throw new Error("workspace-size");
    const parsed = JSON.parse(text);
    state.workspace = sanitizeWorkspace(parsed, true);
    state.workspace.id = activeWorkspaceId();
    localStorage.setItem(LAST_WORKSPACE_KEY, state.workspace.id);
    await persistWorkspace();
    hydrateInputs();
    refreshWorkspaceUI();
    setStatus("shareStatus", t("imported"), "success");
  }

  function projectExportModel(includeNotes) {
    const sequenceEntries = fundingSequenceEntries();
    const sequenceById = new Map(sequenceEntries.map(function (entry) { return [itemId(entry.item), entry]; }));
    const items = savedItems().map(function (item) {
      const sequence = sequenceById.get(itemId(item));
      return {
        item: item,
        phase: state.workspace.roadmapAssignments[itemId(item)] || inferPhase(item),
        deadline: reviewedDeadline(item),
        sequence: sequence ? sequence.sequence : null,
        preparesFor: sequence ? laterFundingTargets(sequenceEntries, sequence.phase, itemId(item)) : [],
      };
    });
    return {
      schema: SCHEMA_VERSION,
      title: state.workspace.projectTitle || t("projectWorkspace"),
      notes: includeNotes ? state.workspace.projectNotes : "",
      profile: state.workspace.profile,
      items: items,
      generatedAt: new Date().toISOString(),
      catalogVersion: catalogVersion(),
    };
  }

  function catalogVersion() {
    return textValue(window.RERC_CATALOG_VERSION, 80) ||
      String(catalog().length) + "-" + textValue(window.RERC_CATALOG && window.RERC_CATALOG.updated, 20);
  }

  function csvCell(value) {
    let text = value == null ? "" : String(value).replace(/\r?\n/g, " ").trim();
    if (/^[=+\-@]/.test(text)) text = "'" + text;
    return '"' + text.replace(/"/g, '""') + '"';
  }

  function exportPlanCsv() {
    const model = projectExportModel(true);
    if (!model.items.length) {
      setStatus("shareStatus", t("noExportItems"), "warning");
      return;
    }
    const headers = [
      "Project title",
      "State or territory",
      "Item ID",
      "Type",
      "Title",
      "Organization",
      "Roadmap phase",
      "Funding sequence order",
      "Phase purpose",
      "Prepares for later saved funding",
      "Status",
      "Eligible applicants",
      "Geography",
      "Project stage",
      "Amount or cost",
      "Match or cost share",
      "Reviewed deadline",
      "Summary",
      "Official source",
      "Project notes",
    ];
    const rows = [headers.map(csvCell).join(",")];
    model.items.forEach(function (entry) {
      const item = entry.item;
      rows.push([
        model.title,
        model.profile.state || "",
        itemId(item),
        item.item_type,
        item.title,
        item.organization,
        entry.phase,
        entry.sequence || "",
        entry.sequence ? phaseStrategy(entry.phase).purpose : "",
        entry.preparesFor.join("; "),
        item.status,
        item.eligible_users,
        item.geography,
        item.project_stage,
        item.amount_or_cost,
        item.match_or_cost,
        entry.deadline ? isoDate(entry.deadline.date) : "",
        summaryFor(item),
        safeHttpUrl(item.source_url),
        model.notes,
      ].map(csvCell).join(","));
    });
    downloadBlob(
      new Blob(["\ufeff" + rows.join("\r\n")], { type: "text/csv;charset=utf-8" }),
      fileStem() + ".csv"
    );
    setStatus("shareStatus", t("csvExported"), "success");
  }

  function xmlEscape(value) {
    return String(value == null ? "" : value)
      .replace(/[\u0000-\u0008\u000B\u000C\u000E-\u001F]/g, "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&apos;");
  }

  function docxParagraph(text, style, relationshipId, pageBreakBefore) {
    const styleXml = style || pageBreakBefore
      ? '<w:pPr>' + (style ? '<w:pStyle w:val="' + xmlEscape(style) + '"/>' : "") +
        (pageBreakBefore ? '<w:pageBreakBefore/>' : "") + '</w:pPr>'
      : "";
    const run = '<w:r><w:t xml:space="preserve">' + xmlEscape(text) + "</w:t></w:r>";
    const content = relationshipId
      ? '<w:hyperlink r:id="' + relationshipId + '" w:history="1"><w:r><w:rPr><w:rStyle w:val="Hyperlink"/></w:rPr><w:t>' +
        xmlEscape(text) + "</w:t></w:r></w:hyperlink>"
      : run;
    return "<w:p>" + styleXml + content + "</w:p>";
  }

  function docxRichParagraph(parts, style) {
    const styleXml = style ? '<w:pPr><w:pStyle w:val="' + xmlEscape(style) + '"/></w:pPr>' : "";
    const runs = parts.map(function (part) {
      const properties = [];
      if (part.bold) properties.push("<w:b/>");
      if (part.italic) properties.push("<w:i/>");
      return "<w:r>" + (properties.length ? "<w:rPr>" + properties.join("") + "</w:rPr>" : "") +
        '<w:t xml:space="preserve">' + xmlEscape(part.text) + "</w:t></w:r>";
    }).join("");
    return "<w:p>" + styleXml + runs + "</w:p>";
  }

  function docxKeyValue(label, value) {
    return docxRichParagraph([{ text: label + ": ", bold: true }, { text: value }], "KeyValue");
  }

  async function exportPlanDocx() {
    const model = projectExportModel(true);
    if (!model.items.length) {
      setStatus("shareStatus", t("noExportItems"), "warning");
      return;
    }
    if (!window.JSZip) throw new Error("jszip-unavailable");
    const relationships = [];
    const body = [];
    body.push(docxParagraph(model.title, "Title"));
    body.push(docxParagraph("Recreation Economy for Rural Communities", "Subtitle"));
    body.push(docxParagraph(t("prepared", { date: new Date().toLocaleDateString(state.language === "es" ? "es-US" : "en-US") }), "Metadata"));
    body.push(docxParagraph(t("communitySnapshot"), "Heading1"));
    profileRows(model.profile).forEach(function (row) {
      body.push(docxKeyValue(row.label, row.value));
    });
    if (model.notes) {
      body.push(docxParagraph(t("projectNotesHeading"), "Heading1"));
      model.notes.split(/\r?\n/).forEach(function (line) { body.push(docxParagraph(line || " ", "BodyText")); });
    }
    body.push(docxParagraph(t("roadmap"), "Heading1"));
    body.push(docxParagraph(t(model.items.length === 1 ? "selectedItemSummary" : "selectedItemsSummary", { count: model.items.length }), "Metadata"));
    const fundingEntries = model.items.filter(function (entry) { return entry.sequence; })
      .sort(function (a, b) { return a.sequence - b.sequence; });
    if (fundingEntries.length) {
      body.push(docxParagraph(t("fundingSequence"), "Heading1"));
      body.push(docxParagraph(t("fundingSequenceSummary", { count: fundingEntries.length }), "Metadata"));
      PHASES.forEach(function (phase) {
        const phaseEntries = fundingEntries.filter(function (entry) { return entry.phase === phase; });
        const strategy = phaseStrategy(phase);
        body.push(docxParagraph(t(phase.toLowerCase()), "Heading2"));
        body.push(docxParagraph(strategy.purpose, "BodyText"));
        body.push(docxParagraph(strategy.outputs, "Metadata"));
        if (!phaseEntries.length) body.push(docxParagraph(t("noPhaseFunding"), "Metadata"));
        phaseEntries.forEach(function (entry) {
          body.push(docxKeyValue(t("sequenceStep", { step: entry.sequence }), textValue(entry.item.title, 500)));
          body.push(docxKeyValue(t("sequenceTiming"), entry.deadline
            ? new Intl.DateTimeFormat(state.language, { year: "numeric", month: "long", day: "numeric" }).format(entry.deadline.date)
            : timingLabel(fundingTimingInfo(entry.item).type)));
          body.push(docxParagraph(entry.preparesFor.length
            ? t("preparesFor") + ": " + entry.preparesFor.join("; ") : t("noLaterTargets"), "BodyText"));
        });
      });
      body.push(docxParagraph(t("fundingSequenceCaveat"), "ClosingNote"));
    }
    PHASES.forEach(function (phase) {
      const entries = model.items.filter(function (entry) { return entry.phase === phase; });
      if (!entries.length) return;
      entries.forEach(function (entry) {
        const item = entry.item;
        body.push(docxParagraph(t(item.item_type === "Funding" ? "fundingCategory" : item.item_type === "Resource" ? "resourceCategory" : "caseStudyCategory").toUpperCase(), "Category", null, true));
        body.push(docxParagraph(t("phaseLabel", { phase: t(phase.toLowerCase()) }), "PhaseLabel"));
        body.push(docxParagraph(textValue(item.title, 500), "Heading2"));
        [
          [t("organization"), item.organization],
          [t("status"), item.status],
          [t("applicant"), item.eligible_users],
          [t("geography"), item.geography],
          [t("stage"), item.project_stage],
          [t("amount"), item.amount_or_cost],
          [t("match"), item.match_or_cost],
          [t("deadline"), item.deadline_or_availability],
        ].forEach(function (row) {
          if (row[1]) body.push(docxKeyValue(row[0], row[1]));
        });
        body.push(docxParagraph(t("overviewHeading"), "Heading3"));
        body.push(docxParagraph(summaryFor(item), "BodyText"));
        const source = safeHttpUrl(item.source_url);
        if (source) {
          const relationshipId = "rId" + (relationships.length + 1);
          relationships.push({ id: relationshipId, url: source });
          body.push(docxParagraph(t("openSource"), "SourceLink", relationshipId));
        }
      });
    });
    body.push(docxParagraph(t("officialEnglish"), "ClosingNote"));

    const documentXml =
      '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' +
      '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" ' +
      'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">' +
      "<w:body>" + body.join("") +
      '<w:sectPr><w:pgSz w:w="12240" w:h="15840"/><w:pgMar w:top="1080" w:right="1080" ' +
      'w:bottom="1080" w:left="1080" w:header="720" w:footer="720" w:gutter="0"/></w:sectPr>' +
      "</w:body></w:document>";
    const relsXml =
      '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' +
      '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">' +
      '<Relationship Id="rIdStyles" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>' +
      relationships.map(function (relationship) {
        return '<Relationship Id="' + relationship.id +
          '" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink" ' +
          'Target="' + xmlEscape(relationship.url) + '" TargetMode="External"/>';
      }).join("") + "</Relationships>";
    const documentLanguage = state.language === "es" ? "es-ES" : "en-US";
    const stylesXml =
      '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' +
      '<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">' +
      '<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/>' +
      '<w:pPr><w:spacing w:after="120" w:line="276" w:lineRule="auto"/></w:pPr><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial"/><w:sz w:val="21"/><w:color w:val="24352F"/><w:lang w:val="' + documentLanguage + '"/></w:rPr></w:style>' +
      '<w:style w:type="paragraph" w:styleId="Title"><w:name w:val="Title"/><w:basedOn w:val="Normal"/>' +
      '<w:pPr><w:spacing w:after="120"/></w:pPr><w:rPr><w:b/><w:color w:val="175641"/><w:sz w:val="38"/></w:rPr></w:style>' +
      '<w:style w:type="paragraph" w:styleId="Subtitle"><w:name w:val="Subtitle"/><w:basedOn w:val="Normal"/>' +
      '<w:rPr><w:i/><w:color w:val="4D6159"/><w:sz w:val="24"/></w:rPr></w:style>' +
      '<w:style w:type="paragraph" w:styleId="Metadata"><w:name w:val="Metadata"/><w:basedOn w:val="Normal"/>' +
      '<w:rPr><w:color w:val="61736C"/><w:sz w:val="19"/></w:rPr></w:style>' +
      '<w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:basedOn w:val="Normal"/><w:qFormat/>' +
      '<w:pPr><w:keepNext/><w:outlineLvl w:val="0"/><w:spacing w:before="240" w:after="100"/><w:pBdr><w:bottom w:val="single" w:sz="12" w:color="D6A525"/></w:pBdr></w:pPr><w:rPr><w:b/><w:color w:val="175641"/><w:sz w:val="28"/></w:rPr></w:style>' +
      '<w:style w:type="paragraph" w:styleId="Heading2"><w:name w:val="heading 2"/><w:basedOn w:val="Normal"/><w:qFormat/>' +
      '<w:pPr><w:keepNext/><w:outlineLvl w:val="1"/><w:spacing w:before="160" w:after="100"/></w:pPr><w:rPr><w:b/><w:color w:val="175641"/><w:sz w:val="28"/></w:rPr></w:style>' +
      '<w:style w:type="paragraph" w:styleId="Heading3"><w:name w:val="heading 3"/><w:basedOn w:val="Normal"/><w:qFormat/>' +
      '<w:pPr><w:keepNext/><w:outlineLvl w:val="2"/><w:spacing w:before="160" w:after="60"/></w:pPr><w:rPr><w:b/><w:color w:val="314A41"/><w:sz w:val="22"/></w:rPr></w:style>' +
      '<w:style w:type="paragraph" w:styleId="Category"><w:name w:val="Category"/><w:basedOn w:val="Normal"/>' +
      '<w:pPr><w:shd w:val="clear" w:color="auto" w:fill="175641"/><w:spacing w:after="80"/><w:ind w:left="120"/></w:pPr><w:rPr><w:b/><w:color w:val="FFFFFF"/><w:sz w:val="20"/></w:rPr></w:style>' +
      '<w:style w:type="paragraph" w:styleId="PhaseLabel"><w:name w:val="Phase Label"/><w:basedOn w:val="Normal"/>' +
      '<w:rPr><w:b/><w:color w:val="8A6B16"/><w:sz w:val="19"/></w:rPr></w:style>' +
      '<w:style w:type="paragraph" w:styleId="KeyValue"><w:name w:val="Key Value"/><w:basedOn w:val="Normal"/>' +
      '<w:pPr><w:spacing w:after="60"/></w:pPr></w:style>' +
      '<w:style w:type="paragraph" w:styleId="BodyText"><w:name w:val="Body Text"/><w:basedOn w:val="Normal"/>' +
      '<w:pPr><w:spacing w:after="160"/></w:pPr></w:style>' +
      '<w:style w:type="paragraph" w:styleId="SourceLink"><w:name w:val="Source Link"/><w:basedOn w:val="Normal"/>' +
      '<w:pPr><w:spacing w:before="120"/></w:pPr></w:style>' +
      '<w:style w:type="paragraph" w:styleId="ClosingNote"><w:name w:val="Closing Note"/><w:basedOn w:val="Normal"/>' +
      '<w:rPr><w:i/><w:color w:val="61736C"/><w:sz w:val="18"/></w:rPr></w:style>' +
      '<w:style w:type="character" w:styleId="Hyperlink"><w:name w:val="Hyperlink"/>' +
      '<w:rPr><w:color w:val="1B6A8F"/><w:u w:val="single"/></w:rPr></w:style></w:styles>';
    const zip = new window.JSZip();
    zip.file("[Content_Types].xml",
      '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' +
      '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">' +
      '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>' +
      '<Default Extension="xml" ContentType="application/xml"/>' +
      '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>' +
      '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>' +
      '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>' +
      '<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>' +
      "</Types>");
    zip.folder("_rels").file(".rels",
      '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' +
      '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">' +
      '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>' +
      '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>' +
      '<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>' +
      "</Relationships>");
    zip.folder("word").file("document.xml", documentXml);
    zip.folder("word").file("styles.xml", stylesXml);
    zip.folder("word").folder("_rels").file("document.xml.rels", relsXml);
    zip.folder("docProps").file("core.xml",
      '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' +
      '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" ' +
      'xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" ' +
      'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><dc:title>' + xmlEscape(model.title) +
      '</dc:title><dc:creator>RERC Community Explorer</dc:creator><dcterms:created xsi:type="dcterms:W3CDTF">' +
      new Date().toISOString() + "</dcterms:created></cp:coreProperties>");
    zip.folder("docProps").file("app.xml",
      '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' +
      '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" ' +
      'xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">' +
      "<Application>RERC Community Explorer</Application></Properties>");
    const blob = await zip.generateAsync({
      type: "blob",
      mimeType: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
      compression: "DEFLATE",
    });
    downloadBlob(blob, fileStem() + ".docx");
    setStatus("shareStatus", t("docxExported"), "success");
  }

  function exportCalendar() {
    const entries = deadlineItems().filter(function (entry) {
      return entry.deadline && entry.deadline.date.getTime() >= new Date().setHours(0, 0, 0, 0);
    });
    if (!entries.length) {
      setStatus("shareStatus", t("noDeadlines"), "warning");
      return;
    }
    const stamp = new Date().toISOString().replace(/[-:]/g, "").replace(/\.\d{3}/, "");
    const lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//RERC Community Explorer//EN", "CALSCALE:GREGORIAN"];
    entries.forEach(function (entry, index) {
      const date = isoDate(entry.deadline.date).replace(/-/g, "");
      const next = new Date(entry.deadline.date);
      next.setDate(next.getDate() + 1);
      lines.push(
        "BEGIN:VEVENT",
        "UID:" + icsEscape(itemId(entry.item) + "-" + date + "@rerc-community-explorer"),
        "DTSTAMP:" + stamp,
        "DTSTART;VALUE=DATE:" + date,
        "DTEND;VALUE=DATE:" + isoDate(next).replace(/-/g, ""),
        "SUMMARY:" + icsEscape(textValue(entry.item.title, 500) + " deadline"),
        "DESCRIPTION:" + icsEscape(
          [summaryFor(entry.item), safeHttpUrl(entry.item.source_url)].filter(Boolean).join("\n")
        ),
        "URL:" + icsEscape(safeHttpUrl(entry.item.source_url)),
        "END:VEVENT"
      );
    });
    lines.push("END:VCALENDAR");
    downloadBlob(
      new Blob([lines.join("\r\n")], { type: "text/calendar;charset=utf-8" }),
      fileStem() + "-deadlines.ics"
    );
    setStatus("shareStatus", t("calendarExported"), "success");
  }

  function icsEscape(value) {
    return String(value || "")
      .replace(/\\/g, "\\\\")
      .replace(/\r?\n/g, "\\n")
      .replace(/,/g, "\\,")
      .replace(/;/g, "\\;");
  }

  function isoDate(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, "0");
    const day = String(date.getDate()).padStart(2, "0");
    return year + "-" + month + "-" + day;
  }

  function fileStem() {
    const base = textValue(state.workspace.projectTitle, 120) ||
      textValue(state.workspace.profile.community || state.workspace.profile.name, 120) ||
      "RERC-Community-Plan";
    return base.replace(/[^A-Za-z0-9._-]+/g, "-").replace(/^-+|-+$/g, "") || "RERC-Community-Plan";
  }

  function downloadBlob(blob, filename) {
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = filename;
    anchor.hidden = true;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    window.setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
  }

  function exportRercie() {
    const communityInput = byId("projectCommunity");
    const community = textValue(communityInput && communityInput.value, 200);
    if (!community) {
      setStatus("shareStatus", t("handoffNeedsCommunity"), "warning");
      if (communityInput) communityInput.focus();
      return;
    }
    const includeNotes = Boolean(byId("includeHandoffNotes") && byId("includeHandoffNotes").checked);
    const model = projectExportModel(includeNotes);
    if (!model.items.length) {
      setStatus("shareStatus", t("noExportItems"), "warning");
      return;
    }
    const profile = {};
    const profileFields = {
      geoid: "geoid", place: "community", geography_type: "placeType",
      population: "population", median_household_income: "medianHouseholdIncome",
      poverty_rate_percent: "povertyRate", source: "source", year: "vintage",
      coverage_note: "coverageNote",
    };
    if (model.profile.geoid) {
      Object.keys(profileFields).forEach(function (key) {
        const value = textValue(model.profile[profileFields[key]], key === "coverage_note" ? 2000 : 300);
        if (value) profile[key] = value;
      });
      const profileSource = safeHttpUrl(model.profile.source_url);
      if (profileSource) profile.source_url = profileSource;
    }
    const selectedRecords = model.items.map(function (entry) {
      const item = entry.item;
      return {
        item_id: itemId(item), item_type: textValue(item.item_type, 40),
        title: textValue(item.title, 500), organization: textValue(item.organization, 500),
        status: textValue(item.status, 200), geography: textValue(item.geography, 500),
        eligible_users: textValue(item.eligible_users, 3000),
        project_stage: textValue(item.project_stage, 500),
        amount_or_cost: textValue(item.amount_or_cost, 2000),
        match_or_cost: textValue(item.match_or_cost, 2000),
        deadline_or_availability: textValue(item.deadline_or_availability, 2000),
        summary: textValue(summaryFor(item), 5000), source_url: safeHttpUrl(item.source_url),
      };
    });
    if (selectedRecords.some(function (record) { return !record.source_url; })) {
      setStatus("shareStatus", t("handoffMissingSource"), "warning");
      return;
    }
    const payload = {
      schema: "rerc-e-handoff",
      version: 1,
      community: community,
      state: textValue(byId("stateSelect") && byId("stateSelect").value, 100),
      projectTitle: textValue(model.title, 300),
      projectNotes: includeNotes ? textValue(model.notes, 12000) : "",
      profile: profile,
      roadmap: model.items.slice(0, 50).map(function (entry) {
        return {
          id: itemId(entry.item), stage: entry.phase,
          title: textValue(entry.item.title, 500),
          status: "Saved for review",
          notes: "Your roadmap phase; confirm the program-supported project stage separately.",
          sourceUrl: safeHttpUrl(entry.item.source_url),
        };
      }),
      selectedRecords: selectedRecords,
    };
    const file = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json;charset=utf-8" });
    if (file.size > MAX_FILE_BYTES) {
      setStatus("shareStatus", t("handoffTooLarge"), "warning");
      return;
    }
    downloadBlob(
      file,
      fileStem() + ".rerc-e"
    );
    const status = byId("shareStatus");
    if (status) {
      status.replaceChildren();
      status.dataset.status = "success";
      status.appendChild(document.createTextNode(t("handoffNextStep") + " "));
    }
  }

  async function deleteLocalData() {
    if (!window.confirm(t("clearHistoryConfirm"))) return;
    // Retain the current community context while replacing the browser-local roadmap.
    // This lets a subsequent state change safely clear any newly added selections.
    const retainedProfile = sanitizeProfile(state.workspace.profile);
    await dbClear(WORKSPACE_STORE);
    const freshWorkspaceId = createWorkspaceId();
    localStorage.setItem(LAST_WORKSPACE_KEY, freshWorkspaceId);
    state.workspace = defaultWorkspace(freshWorkspaceId);
    state.workspace.profile = retainedProfile;
    state.savedOnly = false;
    await persistWorkspace();
    hydrateInputs();
    refreshWorkspaceUI();
    setStatus("shareStatus", t("deleted"), "success");
    setStatus("plannerStatus", t("deleted"), "success");
  }

  function applyLanguage() {
    document.documentElement.lang = state.language;
    if (window.RERCI18N) window.RERCI18N.setLanguage(state.language);
    const labels = {
      showSavedOnly: state.savedOnly ? "allMatches" : "savedOnly",
      openCompare: "compare",
      exportCalendar: "deadlines",
      exportPlanWord: "exportWordAction",
      exportPlanCsv: "exportCsvAction",
      exportWorkspaceFile: "saveWorkspaceAction",
      exportRercie: "handoffDownloadAction",
      openLanguage: "language",
    };
    Object.keys(labels).forEach(function (id) {
      const element = byId(id);
      if (element && element.tagName === "BUTTON") element.setAttribute("aria-label", t(labels[id]));
    });
    const languageButton = byId("openLanguage");
    const languageLabel = languageButton && languageButton.querySelector("span");
    if (languageLabel) languageLabel.textContent = state.language === "es" ? t("spanish") : t("english");
    const mobileNav = byId("plannerMobileNav");
    if (mobileNav) {
      mobileNav.setAttribute("aria-label", t("projectWorkspace"));
      mobileNav.querySelectorAll("[data-label-key]").forEach(function (item) {
        const label = item.querySelector("span:not(.mobile-nav-badge)");
        if (label) label.textContent = t(item.dataset.labelKey);
      });
    }
    ["applicantOptions", "topicOptions"].forEach(function (rootId) {
      const root = byId(rootId);
      if (!root || root.dataset.choicePagerReady !== "true") return;
      const controls = root.nextElementSibling;
      if (!controls || !controls.classList.contains("choice-pager-controls")) return;
      const buttons = controls.querySelectorAll("button");
      if (buttons[0]) { buttons[0].textContent = t("back"); buttons[0].setAttribute("aria-label", t("back") + ": " + t(root.dataset.choiceLabelKey)); }
      if (buttons[1]) { buttons[1].textContent = t("next"); buttons[1].setAttribute("aria-label", t("next") + ": " + t(root.dataset.choiceLabelKey)); }
      const choices = choiceItems(root);
      const current = Number(root.dataset.choicePage || 0);
      const start = current * 6;
      const status = controls.querySelector(".choice-pager-status");
      if (status) status.textContent = t("choicesPage", {
        label: t(root.dataset.choiceLabelKey),
        start: start + 1,
        end: Math.min(start + 6, choices.length),
        total: choices.length,
      });
    });
    const dialog = byId("languageDialog");
    if (dialog) {
      dialog.querySelectorAll("[data-language]").forEach(function (button) {
        const language = button.dataset.language;
        if (button instanceof HTMLInputElement) button.checked = language === state.language;
        else button.setAttribute("aria-pressed", language === state.language ? "true" : "false");
      });
    }
    refreshWorkspaceUI();
  }

  async function setLanguage(language) {
    if (!ALLOWED_LANGUAGES.includes(language)) return;
    state.language = language;
    localStorage.setItem(LANGUAGE_KEY, language);
    applyLanguage();
    closeDialog(byId("languageDialog"));
  }

  function hydrateInputs() {
    const title = byId("projectTitle");
    const notes = byId("projectNotes");
    const community = byId("projectCommunity");
    if (community) community.value = state.workspace.profile.community === state.workspace.profile.state &&
      state.workspace.profile.placeType === "state_or_territory" ? "" : (state.workspace.profile.community || "");
    if (title) title.value = state.workspace.projectTitle;
    if (notes) {
      notes.value = state.workspace.projectNotes;
      notes.maxLength = MAX_NOTES;
    }
    if (typeof explorer().setStateSelection === "function" && state.workspace.profile.stateCode) {
      explorer().setStateSelection(state.workspace.profile.stateCode);
    }
    applyWorkspaceFilters();
  }

  function setupEventHandlers() {
    document.addEventListener("click", function (event) {
      const languageOpener = event.target.closest("#openLanguage");
      if (languageOpener) {
        event.preventDefault();
        openDialog("languageDialog");
        return;
      }
      const communityEntry = event.target.closest("[data-community-entry]");
      if (communityEntry) {
        event.preventDefault();
        revealCommunityForm(true);
        return;
      }
      const action = event.target.closest("[data-action]");
      if (action && action.dataset.itemId) {
        if (action.dataset.action === "planner-save") {
          event.preventDefault();
          toggleSaved(action.dataset.itemId).catch(reportError);
          return;
        }
        if (action.dataset.action === "planner-compare") {
          event.preventDefault();
          toggleCompare(action.dataset.itemId).catch(reportError);
          return;
        }
      }

      const close = event.target.closest("[data-dialog-close]");
      if (close) closeDialog(close.closest("dialog, [role='dialog']"));
      const language = event.target.closest("[data-language]");
      if (language) setLanguage(language.dataset.language).catch(reportError);
    });

    const results = (explorer().elements && explorer().elements.results) || byId("results");
    if (results && window.MutationObserver) {
      state.observer = new MutationObserver(function () {
        window.requestAnimationFrame(decorateResults);
      });
      state.observer.observe(results, { childList: true, subtree: true });
    }
    window.addEventListener("rerc:render", function () {
      if (state.savedOnly) renderSavedOnly();
      else window.requestAnimationFrame(decorateResults);
    });

    bind("showSavedOnly", "click", function (event) {
      toggleSavedOnly(event.currentTarget.type === "checkbox" ? event.currentTarget.checked : undefined);
    });
    bind("openCompare", "click", function () { renderComparison(); openDialog("compareDialog"); });
    bind("compareSaved", "click", function () { renderComparison(); openDialog("compareDialog"); });
    bind("toggleSavedTray", "click", function (event) {
      const tray = byId("savedTray");
      if (!tray) return;
      const expanded = event.currentTarget.getAttribute("aria-expanded") === "true";
      event.currentTarget.setAttribute("aria-expanded", expanded ? "false" : "true");
      tray.hidden = expanded;
      if (!expanded) {
        const focusable = tray.querySelector("button, a, select");
        if (focusable) focusable.focus();
      }
    });
    bind("exportPlanWord", "click", function () { exportPlanDocx().catch(reportError); });
    bind("exportPlanCsv", "click", exportPlanCsv);
    bind("exportWorkspaceFile", "click", exportWorkspace);
    bind("exportRercie", "click", exportRercie);
    bind("deleteLocalData", "click", function () { deleteLocalData().catch(reportError); });
    bind("shareWorkspace", "click", showShareDialog);
    bind("copyShareLink", "click", function () { copyShareLink().catch(reportError); });


    const importInput = byId("importWorkspaceFile");
    if (importInput) {
      importInput.accept = ".rerc-workspace,application/json";
      importInput.addEventListener("change", function () {
        const file = importInput.files && importInput.files[0];
        importWorkspace(file).catch(function (error) {
          setStatus("shareStatus", t("invalidWorkspace"), "error");
          reportError(error);
        }).finally(function () { importInput.value = ""; });
      });
    }

    const title = byId("projectTitle");
    if (title) {
      title.maxLength = 200;
      title.addEventListener("input", function () {
        state.workspace.projectTitle = title.value.slice(0, 200);
        schedulePersist();
      });
    }
    const notes = byId("projectNotes");
    if (notes) {
      notes.maxLength = MAX_NOTES;
      notes.addEventListener("input", function () {
        state.workspace.projectNotes = notes.value.slice(0, MAX_NOTES);
        schedulePersist();
      });
    }
    const projectCommunity = byId("projectCommunity");
    if (projectCommunity) {
      projectCommunity.addEventListener("input", captureProfileFromFilters);
    }
    function emptyStateWorkspace() {
      state.workspace.savedIds = [];
      state.workspace.compareIds = [];
      state.workspace.roadmapAssignments = {};
      state.workspace.projectTitle = "";
      state.workspace.projectNotes = "";
      state.workspace.filters = {};
      state.savedOnly = false;
    }

    function profileForState(control) {
      const option = control && control.options ? control.options[control.selectedIndex] : null;
      const value = textValue(control && control.value, 120);
      const label = textValue(option && option.text, 120) || value;
      return sanitizeProfile(value ? { state: label, stateCode: value, name: label, placeType: "state_or_territory" } : {});
    }

    const communityState = byId("stateSelect");
    if (communityState) {
      communityState.addEventListener("change", function () {
        const previousState = textValue(state.workspace.profile.stateCode, 120);
        const nextState = textValue(communityState.value, 120);
        if (previousState && nextState && previousState !== nextState) {
          emptyStateWorkspace();
          state.workspace.profile = profileForState(communityState);
          const title = byId("projectTitle");
          const notes = byId("projectNotes");
          const projectCommunity = byId("projectCommunity");
          if (title) title.value = "";
          if (notes) notes.value = "";
          if (projectCommunity) projectCommunity.value = "";
          persistWorkspace().then(refreshWorkspaceUI).catch(reportError);
          setStatus("profileStatus", t("stateChanged"), "info");
        }
        communityState.setCustomValidity("");
        communityState.removeAttribute("aria-invalid");
        syncCommunityGate();
      });
    }

    bind("resetStateSelection", "click", function () {
      if (state.workspace.savedIds.length && !window.confirm(t("clearStateConfirm"))) return;
      emptyStateWorkspace();
      state.workspace.profile = sanitizeProfile({});
      const title = byId("projectTitle");
      const notes = byId("projectNotes");
      const projectCommunity = byId("projectCommunity");
      if (title) title.value = "";
      if (notes) notes.value = "";
      if (projectCommunity) projectCommunity.value = "";
      if (typeof explorer().setStateSelection === "function") explorer().setStateSelection("");
      persistWorkspace().then(function () {
        if (typeof state.showWizardStep === "function") state.showWizardStep(1, { focus: false });
        else revealCommunityForm(false);
        refreshWorkspaceUI();
        syncCommunityGate();
        setStatus("profileStatus", t("stateReset"), "info");
        if (communityState) communityState.focus({ preventScroll: true });
      }).catch(reportError);
    });

    const filters = byId("communityFilters");
    if (filters) {
      filters.addEventListener("change", function (event) {
        captureProfileFromFilters();
        captureWorkspaceFilters();
        syncCommunityGate();
      });
    }
    const resultsToolbar = byId("resultsToolbar");
    if (resultsToolbar) resultsToolbar.addEventListener("change", captureWorkspaceFilters);
    const keywordSearch = byId("keywordSearch");
    if (keywordSearch) keywordSearch.addEventListener("input", captureWorkspaceFilters);
    document.querySelectorAll("[data-mode], #resetButton").forEach(function (control) {
      control.addEventListener("click", function () { window.setTimeout(captureWorkspaceFilters, 0); });
    });
    const roadmap = byId("roadmap");
    if (roadmap) {
      roadmap.addEventListener("change", function (event) {
        const select = event.target.closest("[data-roadmap-id]");
        if (!select || !PHASES.includes(select.value)) return;
        state.workspace.roadmapAssignments[select.dataset.roadmapId] = select.value;
        persistWorkspace().then(function () {
          refreshWorkspaceUI();
          setStatus("plannerStatus", t("phaseChanged", { phase: t(select.value.toLowerCase()) }), "success");
        }).catch(reportError);
      });
    }
  }

  function bind(id, eventName, handler) {
    const element = byId(id);
    if (element) element.addEventListener(eventName, handler);
  }

  async function initialize() {
    state.language = ALLOWED_LANGUAGES.includes(localStorage.getItem(LANGUAGE_KEY))
      ? localStorage.getItem(LANGUAGE_KEY)
      : "en";
    state.db = await openDatabase();
    const workspaceId = activeWorkspaceId();
    const stored = await dbGet(WORKSPACE_STORE, workspaceId);
    try {
      state.workspace = stored ? sanitizeWorkspace(stored, false) : defaultWorkspace(workspaceId);
    } catch (error) {
      reportError(error);
      state.workspace = defaultWorkspace(workspaceId);
    }
    localStorage.setItem(LAST_WORKSPACE_KEY, state.workspace.id);
    await importShareFromHash();
    hydrateInputs();
    setupWizard();
    setupChoicePager("applicantOptions", "applicantChoices");
    setupChoicePager("topicOptions", "topicChoices");
    setupMobileNavigation();
    setupEventHandlers();
    applyLanguage();
    refreshWorkspaceUI();
    syncCommunityGate();
    document.documentElement.classList.add("rerc-planner-ready");
    document.dispatchEvent(new CustomEvent("rerc:planner-ready", {
      detail: { schema: SCHEMA_VERSION, workspaceId: state.workspace.id },
    }));
  }

  function start() {
    if (!window.RERCExplorer) {
      window.setTimeout(start, 25);
      return;
    }
    initialize().catch(function (error) {
      reportError(error);
      document.documentElement.classList.add("rerc-planner-error");
      setStatus("shareStatus", t("startupError"), "error");
    });
  }

  window.RERCPlannerView = {
    getActiveMatches: function () { return state.savedOnly ? savedItems() : null; },
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start, { once: true });
  } else {
    start();
  }
})();
