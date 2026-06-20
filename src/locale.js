const CATALOGS = Object.freeze({
  "pt-BR": {
    documentTitle: "Live Therapy — Sessão com {name}", description: "Assistente de apoio psicológico por voz, privada e hospedada na rede local.", imageAlt: "{name} sorrindo em um consultório acolhedor", skip: "Ir para o conteúdo",
    sessionControls: "Controles da sessão", sessionEnded: "Sessão finalizada", sessionCancelled: "Sessão cancelada", sessionSummary: "Resumo da sessão",
    localReady: "Servidor local pronto", connecting: "Conectando ao servidor…", sessionWith: "Sua sessão com {name}", microphoneNotice: "Ao iniciar, o navegador pedirá acesso ao microfone somente durante esta sessão.",
    disclaimer: "{name} é uma assistente virtual de apoio psicológico e não substitui atendimento profissional ou de emergência.", startSession: "Iniciar sessão", providerWarning: "O servidor está ativo, mas as chaves dos provedores ainda precisam ser configuradas.",
    volumeOpen: "Abrir controle de volume", volumeClose: "Fechar controle de volume", volume: "Volume", sessionVolume: "Volume da sessão: {value}%",
    microphone: "Microfone", micEnable: "Ativar microfone", micDisable: "Desativar microfone", micLocked: "Microfone bloqueado enquanto {name} responde", waitForVoice: "Aguarde {name} terminar",
    settings: "Configurações", moreOptions: "Mais opções", sessionTopics: "Tópicos da sessão", moveTopics: "Mover painel de tópicos com o mouse, toque ou teclas de seta",
    expandTopics: "Expandir tópicos", minimizeTopics: "Minimizar tópicos", newTopic: "Novo tópico", newTopicPlaceholder: "Digite um novo ponto", add: "Adicionar", cancel: "Cancelar", end: "Encerrar",
    sessionStage: "Sessão com {name}", retry: "Tentar novamente", completedMessage: "Esperamos que este tempo tenha sido acolhedor e proveitoso para você.", cancelledMessage: "Você pode recomeçar quando se sentir confortável.",
    completedTopics: "Tópicos concluídos", closingQuote: "“O autoconhecimento é um caminho contínuo. Respire fundo e aproveite seu descanso.”", detailedSummary: "Ver resumo detalhado", backHome: "Voltar ao início",
    privacyNote: "Sessão local — o áudio temporário não é armazenado", back: "← Voltar", sessionLabel: "Sessão com {name}", yourSummary: "Seu resumo", summaryPending: "O resumo está sendo preparado e ficará disponível em instantes.",
    sessionTime: "tempo de sessão", topicsCompleted: "tópicos concluídos", topics: "Tópicos", completed: "Concluído", later: "Para retomar depois",
    reflectionTitle: "Reflexão para levar com você", reflection: "Reserve alguns minutos para reconhecer como você se sente agora. Pequenos momentos de presença também fazem parte do caminho.", finishAndHome: "Concluir e voltar ao início",
    micOffStatus: "Microfone desativado", readyStatus: "Pronta para ouvir", listeningStatus: "Ouvindo você", recordingStatus: "Você está falando", processingStatus: "{name} está refletindo…", speakingStatus: "{name} está falando",
    errorStatus: "A sessão precisa de atenção", activeStatus: "Sessão ativa", serverUnavailable: "Servidor indisponível", localServerError: "Não foi possível acessar o servidor local.", sessionNotStarted: "A sessão ainda não foi iniciada.",
    requestFailed: "O servidor não conseguiu concluir a solicitação.", startFailed: "Não foi possível iniciar a sessão.", voiceFailed: "Não foi possível processar sua fala.", playbackFailed: "Não foi possível reproduzir a resposta de voz.",
    secureMicrophone: "O microfone exige uma conexão HTTPS segura.", unsupportedCapture: "Este navegador não oferece captura de voz compatível.", themeLight: "claro", themeDark: "escuro", switchTheme: "Mudar para tema {theme}", themeTitle: "Tema {theme}",
  },
  "en-US": {
    documentTitle: "Live Therapy — Session with {name}", description: "Private local voice-based psychological support assistant.", imageAlt: "{name} smiling in a welcoming office", skip: "Skip to content",
    sessionControls: "Session controls", sessionEnded: "Session ended", sessionCancelled: "Session cancelled", sessionSummary: "Session summary", localReady: "Local server ready", connecting: "Connecting to server…",
    sessionWith: "Your session with {name}", microphoneNotice: "When you begin, the browser will request microphone access only for this session.", disclaimer: "{name} is a virtual psychological support assistant and does not replace professional or emergency care.",
    startSession: "Start session", providerWarning: "The server is active, but provider credentials still need configuration.", volumeOpen: "Open volume control", volumeClose: "Close volume control", volume: "Volume", sessionVolume: "Session volume: {value}%",
    microphone: "Microphone", micEnable: "Enable microphone", micDisable: "Disable microphone", micLocked: "Microphone locked while {name} responds", waitForVoice: "Wait for {name} to finish", settings: "Settings", moreOptions: "More options",
    sessionTopics: "Session topics", moveTopics: "Move topics panel with mouse, touch, or arrow keys", expandTopics: "Expand topics", minimizeTopics: "Minimize topics", newTopic: "New topic", newTopicPlaceholder: "Enter a new point", add: "Add", cancel: "Cancel", end: "End",
    sessionStage: "Session with {name}", retry: "Try again", completedMessage: "We hope this time felt supportive and useful.", cancelledMessage: "You can begin again when you feel comfortable.", completedTopics: "Completed topics",
    closingQuote: "“Self-knowledge is an ongoing path. Take a breath and enjoy your rest.”", detailedSummary: "View detailed summary", backHome: "Back to start", privacyNote: "Local session — temporary audio is not stored", back: "← Back",
    sessionLabel: "Session with {name}", yourSummary: "Your summary", summaryPending: "Your summary is being prepared.", sessionTime: "session time", topicsCompleted: "topics completed", topics: "Topics", completed: "Completed", later: "Return to later",
    reflectionTitle: "Reflection to take with you", reflection: "Take a moment to notice how you feel now. Small moments of presence are also part of the path.", finishAndHome: "Finish and return to start",
    micOffStatus: "Microphone off", readyStatus: "Ready to listen", listeningStatus: "Listening", recordingStatus: "You are speaking", processingStatus: "{name} is reflecting…", speakingStatus: "{name} is speaking", errorStatus: "The session needs attention", activeStatus: "Session active",
    serverUnavailable: "Server unavailable", localServerError: "Could not reach the local server.", sessionNotStarted: "The session has not started.", requestFailed: "The server could not complete the request.", startFailed: "Could not start the session.", voiceFailed: "Could not process your speech.",
    playbackFailed: "Could not play the voice response.", secureMicrophone: "The microphone requires a secure HTTPS connection.", unsupportedCapture: "This browser does not support compatible voice capture.", themeLight: "light", themeDark: "dark", switchTheme: "Switch to {theme} theme", themeTitle: "{theme} theme",
  },
});

export const DEFAULT_LANGUAGE = "pt-BR";
export const SUPPORTED_UI_LANGUAGES = Object.freeze(Object.keys(CATALOGS));

export function translate(language, key, variables = {}) {
  const catalog = CATALOGS[language] ?? CATALOGS[DEFAULT_LANGUAGE];
  const value = catalog[key] ?? CATALOGS[DEFAULT_LANGUAGE][key] ?? key;
  if (typeof value !== "string") return value;
  return value.replace(/\{(\w+)\}/g, (_, name) => String(variables[name] ?? ""));
}

export function initialTopics() {
  return [];
}
