self.addEventListener('install', (e) => {
  console.log('VaperApp: Service Worker Instalado');
});

self.addEventListener('fetch', (e) => {
  // Aquí podrías agregar lógica para usar la app sin internet
});