import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';

const resources = {
    en: {
        translation: {
            // Navigation
            "nav.dashboard": "Dashboard",
            "nav.settings": "Settings",
            "nav.logs": "Logs",
            "nav.logout": "Logout",

            // Dashboard
            "dashboard.title": "My Library",
            "dashboard.search": "Search publications...",
            "dashboard.continueReading": "Continue Reading",
            "dashboard.all": "All",
            "dashboard.newspapers": "📰 Newspapers",
            "dashboard.magazines": "📑 Magazines",
            "dashboard.others": "📂 Others",
            "dashboard.noPublications": "No publications found",
            "dashboard.loading": "Loading your library...",

            // Reader
            "reader.page": "Page",
            "reader.of": "of",
            "reader.loading": "Loading PDF...",
            "reader.error": "Error loading PDF",

            // Settings
            "settings.title": "Settings",
            "settings.users": "User Management",
            "settings.content": "Content Rules",
            "settings.telegram": "Telegram",
            "settings.ai": "AI Settings",
            "settings.systemControl": "System Control",
            "settings.botStatus": "Bot Status",
            "settings.running": "Running",
            "settings.stopped": "Stopped",
            "settings.filesDownloaded": "Files Downloaded",
            "settings.startBot": "Start Bot",
            "settings.stopBot": "Stop Bot",
            "settings.manualScan": "Manual Scan",
            "settings.scanChannel": "Scan Channel",
            "settings.processOthers": "Process \"Others\" Files",
            "settings.removeDuplicates": "Remove Duplicates",
            "settings.publications": "Publications",
            "settings.categories": "Categories",
            "settings.language": "Language",
            "settings.selectLanguage": "Select Language",
            "settings.statistics": "Statistics",
            "settings.totalPublications": "Total Publications",
            "settings.totalCategories": "Total Categories",
            "settings.diskUsage": "Disk Usage",

            // Logs
            "logs.title": "System Logs",
            "logs.refresh": "Refresh",
            "logs.clear": "Clear",
            "logs.autoRefresh": "Auto-refresh",
            "logs.loading": "Loading logs...",
            "logs.noLogs": "No logs available",

            // Login/Register
            "auth.login": "Login",
            "auth.register": "Register",
            "auth.username": "Username",
            "auth.email": "Email",
            "auth.password": "Password",
            "auth.confirmPassword": "Confirm Password",
            "auth.forgotPassword": "Forgot Password?",
            "auth.noAccount": "Don't have an account?",
            "auth.haveAccount": "Already have an account?",
            "auth.signIn": "Sign In",
            "auth.signUp": "Sign Up",
            "auth.welcome": "Welcome to Banca",
            "auth.welcomeBack": "Welcome back",

            // Common
            "common.save": "Save",
            "common.cancel": "Cancel",
            "common.delete": "Delete",
            "common.edit": "Edit",
            "common.close": "Close",
            "common.confirm": "Confirm",
            "common.yes": "Yes",
            "common.no": "No",
            "common.error": "Error",
            "common.success": "Success",
            "common.loading": "Loading...",
            "common.clear": "Clear",
            "common.back": "Back",
            "common.logout": "Logout",
        }
    },
    pt: {
        translation: {
            // Navigation
            "nav.dashboard": "Painel",
            "nav.settings": "Configurações",
            "nav.logs": "Registos",
            "nav.logout": "Sair",

            // Dashboard
            "dashboard.title": "Minha Biblioteca",
            "dashboard.search": "Pesquisar publicações...",
            "dashboard.continueReading": "Continuar a Ler",
            "dashboard.all": "Todos",
            "dashboard.newspapers": "📰 Jornais",
            "dashboard.magazines": "📑 Revistas",
            "dashboard.others": "📂 Outros",
            "dashboard.noPublications": "Nenhuma publicação encontrada",
            "dashboard.loading": "Carregando sua biblioteca...",

            // Reader
            "reader.page": "Página",
            "reader.of": "de",
            "reader.loading": "Carregando PDF...",
            "reader.error": "Erro ao carregar PDF",

            // Settings
            "settings.title": "Configurações",
            "settings.users": "Gestão de Utilizadores",
            "settings.content": "Regras de Conteúdo",
            "settings.telegram": "Telegram",
            "settings.ai": "Definições de IA",
            "settings.systemControl": "Controle do Sistema",
            "settings.botStatus": "Estado do Bot",
            "settings.running": "Em Execução",
            "settings.stopped": "Parado",
            "settings.filesDownloaded": "Ficheiros Descarregados",
            "settings.startBot": "Iniciar Bot",
            "settings.stopBot": "Parar Bot",
            "settings.manualScan": "Digitalização Manual",
            "settings.scanChannel": "Digitalizar Canal",
            "settings.processOthers": "Processar Ficheiros \"Others\"",
            "settings.removeDuplicates": "Remover Duplicados",
            "settings.publications": "Publicações",
            "settings.categories": "Categorias",
            "settings.language": "Idioma",
            "settings.selectLanguage": "Selecionar Idioma",
            "settings.statistics": "Estatísticas",
            "settings.totalPublications": "Total de Publicações",
            "settings.totalCategories": "Total de Categorias",
            "settings.diskUsage": "Uso de Disco",

            // Logs
            "logs.title": "Registos do Sistema",
            "logs.refresh": "Atualizar",
            "logs.clear": "Limpar",
            "logs.autoRefresh": "Atualização automática",
            "logs.loading": "Carregando registos...",
            "logs.noLogs": "Nenhum registo disponível",

            // Login/Register
            "auth.login": "Entrar",
            "auth.register": "Registar",
            "auth.username": "Nome de utilizador",
            "auth.email": "Email",
            "auth.password": "Palavra-passe",
            "auth.confirmPassword": "Confirmar Palavra-passe",
            "auth.forgotPassword": "Esqueceu a palavra-passe?",
            "auth.noAccount": "Não tem uma conta?",
            "auth.haveAccount": "Já tem uma conta?",
            "auth.signIn": "Iniciar Sessão",
            "auth.signUp": "Criar Conta",
            "auth.welcome": "Bem-vindo ao Banca",
            "auth.welcomeBack": "Bem-vindo de volta",

            // Common
            "common.save": "Guardar",
            "common.cancel": "Cancelar",
            "common.delete": "Eliminar",
            "common.edit": "Editar",
            "common.close": "Fechar",
            "common.confirm": "Confirmar",
            "common.yes": "Sim",
            "common.no": "Não",
            "common.error": "Erro",
            "common.success": "Sucesso",
            "common.loading": "Carregando...",
            "common.clear": "Limpar",
            "common.back": "Voltar",
            "common.logout": "Sair",
        }
    },
    es: {
        translation: {
            // Navigation
            "nav.dashboard": "Panel",
            "nav.settings": "Configuración",
            "nav.logs": "Registros",
            "nav.logout": "Cerrar Sesión",

            // Dashboard
            "dashboard.title": "Mi Biblioteca",
            "dashboard.search": "Buscar publicaciones...",
            "dashboard.continueReading": "Continuar Leyendo",
            "dashboard.all": "Todos",
            "dashboard.newspapers": "📰 Periódicos",
            "dashboard.magazines": "📑 Revistas",
            "dashboard.others": "📂 Otros",
            "dashboard.noPublications": "No se encontraron publicaciones",
            "dashboard.loading": "Cargando tu biblioteca...",

            // Reader
            "reader.page": "Página",
            "reader.of": "de",
            "reader.loading": "Cargando PDF...",
            "reader.error": "Error al cargar PDF",

            // Settings
            "settings.title": "Configuración",
            "settings.users": "Gestión de Usuarios",
            "settings.content": "Reglas de Contenido",
            "settings.telegram": "Telegram",
            "settings.ai": "Ajustes de IA",
            "settings.systemControl": "Control del Sistema",
            "settings.botStatus": "Estado del Bot",
            "settings.running": "En Ejecución",
            "settings.stopped": "Detenido",
            "settings.filesDownloaded": "Archivos Descargados",
            "settings.startBot": "Iniciar Bot",
            "settings.stopBot": "Detener Bot",
            "settings.manualScan": "Escaneo Manual",
            "settings.scanChannel": "Escanear Canal",
            "settings.processOthers": "Procesar Archivos \"Others\"",
            "settings.removeDuplicates": "Eliminar Duplicados",
            "settings.publications": "Publicaciones",
            "settings.categories": "Categorías",
            "settings.language": "Idioma",
            "settings.selectLanguage": "Seleccionar Idioma",
            "settings.statistics": "Estadísticas",
            "settings.totalPublications": "Total de Publicaciones",
            "settings.totalCategories": "Total de Categorías",
            "settings.diskUsage": "Uso de Disco",

            // Logs
            "logs.title": "Registros del Sistema",
            "logs.refresh": "Actualizar",
            "logs.clear": "Limpiar",
            "logs.autoRefresh": "Actualización automática",
            "logs.loading": "Cargando registros...",
            "logs.noLogs": "No hay registros disponibles",

            // Login/Register
            "auth.login": "Iniciar Sesión",
            "auth.register": "Registrarse",
            "auth.username": "Nombre de usuario",
            "auth.email": "Correo electrónico",
            "auth.password": "Contraseña",
            "auth.confirmPassword": "Confirmar Contraseña",
            "auth.forgotPassword": "¿Olvidaste tu contraseña?",
            "auth.noAccount": "¿No tienes una cuenta?",
            "auth.haveAccount": "¿Ya tienes una cuenta?",
            "auth.signIn": "Iniciar Sesión",
            "auth.signUp": "Crear Cuenta",
            "auth.welcome": "Bienvenido a Banca",
            "auth.welcomeBack": "Bienvenido de nuevo",

            // Common
            "common.save": "Guardar",
            "common.cancel": "Cancelar",
            "common.delete": "Eliminar",
            "common.edit": "Editar",
            "common.close": "Cerrar",
            "common.confirm": "Confirmar",
            "common.yes": "Sí",
            "common.no": "No",
            "common.error": "Error",
            "common.success": "Éxito",
            "common.loading": "Cargando...",
            "common.clear": "Limpiar",
            "common.back": "Volver",
            "common.logout": "Cerrar sesión",
        }
    },
    nl: {
        translation: {
            // Navigation
            "nav.dashboard": "Dashboard",
            "nav.settings": "Instellingen",
            "nav.logs": "Logboeken",
            "nav.logout": "Uitloggen",

            // Dashboard
            "dashboard.title": "Mijn Bibliotheek",
            "dashboard.search": "Zoek publicaties...",
            "dashboard.continueReading": "Verder Lezen",
            "dashboard.all": "Alle",
            "dashboard.newspapers": "📰 Kranten",
            "dashboard.magazines": "📑 Tijdschriften",
            "dashboard.others": "📂 Overigen",
            "dashboard.noPublications": "Geen publicaties gevonden",
            "dashboard.loading": "Bibliotheek laden...",

            // Reader
            "reader.page": "Pagina",
            "reader.of": "van",
            "reader.loading": "PDF laden...",
            "reader.error": "Fout bij laden PDF",

            // Settings
            "settings.title": "Instellingen",
            "settings.users": "Gebruikersbeheer",
            "settings.content": "Inhoudsregels",
            "settings.telegram": "Telegram",
            "settings.ai": "AI-instellingen",
            "settings.systemControl": "Systeembeheer",
            "settings.botStatus": "Bot Status",
            "settings.running": "Actief",
            "settings.stopped": "Gestopt",
            "settings.filesDownloaded": "Bestanden Gedownload",
            "settings.startBot": "Start Bot",
            "settings.stopBot": "Stop Bot",
            "settings.manualScan": "Handmatige Scan",
            "settings.scanChannel": "Scan Kanaal",
            "settings.processOthers": "Verwerk \"Others\" Bestanden",
            "settings.removeDuplicates": "Verwijder Duplicaten",
            "settings.publications": "Publicaties",
            "settings.categories": "Categorieën",
            "settings.language": "Taal",
            "settings.selectLanguage": "Selecteer Taal",
            "settings.statistics": "Statistieken",
            "settings.totalPublications": "Totaal Publicaties",
            "settings.totalCategories": "Totaal Categorieën",
            "settings.diskUsage": "Schijfgebruik",

            // Logs
            "logs.title": "Systeem Logboeken",
            "logs.refresh": "Vernieuwen",
            "logs.clear": "Wissen",
            "logs.autoRefresh": "Automatisch vernieuwen",
            "logs.loading": "Logboeken laden...",
            "logs.noLogs": "Geen logboeken beschikbaar",

            // Login/Register
            "auth.login": "Inloggen",
            "auth.register": "Registreren",
            "auth.username": "Gebruikersnaam",
            "auth.email": "E-mail",
            "auth.password": "Wachtwoord",
            "auth.confirmPassword": "Bevestig Wachtwoord",
            "auth.forgotPassword": "Wachtwoord vergeten?",
            "auth.noAccount": "Heb je geen account?",
            "auth.haveAccount": "Heb je al een account?",
            "auth.signIn": "Inloggen",
            "auth.signUp": "Account Aanmaken",
            "auth.welcome": "Welkom bij Banca",
            "auth.welcomeBack": "Welkom terug",

            // Common
            "common.save": "Opslaan",
            "common.cancel": "Annuleren",
            "common.delete": "Verwijderen",
            "common.edit": "Bewerken",
            "common.close": "Sluiten",
            "common.confirm": "Bevestigen",
            "common.yes": "Ja",
            "common.no": "Nee",
            "common.error": "Fout",
            "common.success": "Succes",
            "common.loading": "Laden...",
            "common.clear": "Wissen",
            "common.back": "Terug",
            "common.logout": "Uitloggen",
        }
    }
};

i18n
    .use(LanguageDetector)
    .use(initReactI18next)
    .init({
        resources,
        fallbackLng: 'pt',
        debug: false,
        interpolation: {
            escapeValue: false,
        },
        detection: {
            order: ['localStorage', 'navigator'],
            caches: ['localStorage'],
        }
    });

export default i18n;
