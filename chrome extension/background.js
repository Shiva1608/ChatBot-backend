chrome.contextMenus.create({
    id: "captureURL",
    title: "Capture URL",
    contexts: ["page", "link", "selection", "image", "video"]
  });

  chrome.contextMenus.onClicked.addListener(function(info, tabs) {
    if (info.menuItemId === "captureURL") {
      chrome.tabs.query({active: true, currentWindow: true}, function(tabs) {
        var currentTab = tabs[0];
        if (currentTab) {
          console.log("Captured URL: " + currentTab.url);
          getData(currentTab.url);
        }
      });
    }
  });



  function getData(url) {
    if (!url.includes("youtube.com")) {
      fetch(
        'http://localhost:5001/update_url_vdb', 
        {
          method: 'POST', 
          headers: {'Access-Control-Allow-Origin': '*', 'Content-Type': 'application/json'},
          body: JSON.stringify({
            url: url,
            category: "Testing"
        })
        },
        
      )
      .then(
      res => console.log(res)
      )
      return
    }
    else {
      fetch(
        'http://localhost:5001/update_yt_url_vdb', 
        {
          method: 'POST', 
          headers: {'Access-Control-Allow-Origin': '*', 'Content-Type': 'application/json'},
          body: JSON.stringify({
            url: url,
            category: "Testing"
        })
        },
        
      )
      .then(
      res => console.log(res)
      )
      return
    }
  }