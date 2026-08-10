(function () {
  "use strict";

  const formConfig = window.RERC_SITE_CONFIG && window.RERC_SITE_CONFIG.contributions;
  if (!formConfig) return;

  function publicFormUrl(value) {
    try {
      const url = new URL(value);
      if (url.origin !== "https://docs.google.com" || !url.pathname.includes("/forms/")) return null;
      return url;
    } catch (_) {
      return null;
    }
  }

  function embeddedUrl(url) {
    const embedded = new URL(url.toString());
    embedded.search = "";
    embedded.searchParams.set("embedded", "true");
    return embedded.toString();
  }

  function wireContribution({ buttonId, dialogId, frameId, externalId, sourceUrl }) {
    const button = document.getElementById(buttonId);
    const dialog = document.getElementById(dialogId);
    const frame = document.getElementById(frameId);
    const external = document.getElementById(externalId);
    const publicUrl = publicFormUrl(sourceUrl);
    if (!button || !dialog || !frame || !external || !publicUrl) return;

    external.href = publicUrl.toString();
    button.addEventListener("click", () => {
      frame.src = embeddedUrl(publicUrl);
      dialog.showModal();
    });
    dialog.querySelectorAll("[data-close-contribution]").forEach((control) => {
      control.addEventListener("click", () => dialog.close());
    });
  }

  wireContribution({
    buttonId: "openIssueReport",
    dialogId: "issueReportDialog",
    frameId: "issueReportFrame",
    externalId: "issueReportExternal",
    sourceUrl: formConfig.issueReportUrl
  });
  wireContribution({
    buttonId: "openCatalogSubmission",
    dialogId: "catalogSubmissionDialog",
    frameId: "catalogSubmissionFrame",
    externalId: "catalogSubmissionExternal",
    sourceUrl: formConfig.catalogSubmissionUrl
  });
}());
