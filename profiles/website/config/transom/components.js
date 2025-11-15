window.addEventListener("load", () => {
    const tocNav = $("nav.transom-page-toc");

    if (!tocNav || !tocNav.$("a")) {
        return;
    }

    const updateHeadingSelection = () => {
        const currHash = window.location.hash;

        for (const elem of tocNav.$$(".selected")) {
            elem.classList.remove("selected");
        }

        if (currHash) {
            for (const link of tocNav.$$("a")) {
                const linkHash = new URL(link.href).hash;

                if (linkHash === currHash) {
                    link.classList.add("selected");
                    break;
                }
            }

            $(currHash).parentElement.parentElement.classList.add("selected");
        } else {
            // Select the top heading by default
            tocNav.$("a").classList.add("selected");
        }
    }

    updateHeadingSelection();

    window.addEventListener("hashchange", updateHeadingSelection);
});
