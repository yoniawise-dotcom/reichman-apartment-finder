document.getElementById('copy').addEventListener('click', async () => {
  const [tab] = await chrome.tabs.query({active:true,currentWindow:true});
  const [{result}] = await chrome.scripting.executeScript({target:{tabId:tab.id},func:() => {
    const text = document.body.innerText.slice(0,15000);
    const links = [...document.querySelectorAll('a[href]')].map(a=>a.href).filter(h=>h.startsWith('http'));
    return `${location.href}\n\n${text}\n\nLinks:\n${[...new Set(links)].slice(0,40).join('\n')}`;
  }});
  await navigator.clipboard.writeText(result);
  document.getElementById('status').textContent='Copied — paste into the finder.';
});
