// Если открыли popup как расширение, сразу открываем отдельное окно и закрываем popup
if (window.location.pathname.endsWith('index.html')) {
  window.open(
    chrome.runtime.getURL('normal_popup.html'),
    'findmylink_popup',
    'width=380,height=600'
  );
  window.close();
}
