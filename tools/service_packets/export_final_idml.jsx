(function () {
    if (app.documents.length !== 0) throw Error('user_documents_open');
    var doc = null;
    var oldInteraction = app.scriptPreferences.userInteractionLevel;
    try {
        app.scriptPreferences.userInteractionLevel = UserInteractionLevels.NEVER_INTERACT;
        doc = app.open(File(job.input), false);
        doc.recompose();
        var overset = 0, badFonts = 0, badLinks = 0;
        for (var i = 0; i < doc.stories.length; i++) {
            if (doc.stories[i].overflows) overset++;
        }
        for (var f = 0; f < doc.fonts.length; f++) {
            if (doc.fonts[f].status !== FontStatus.INSTALLED) badFonts++;
        }
        for (var l = 0; l < doc.links.length; l++) {
            if (doc.links[l].status !== LinkStatus.NORMAL && doc.links[l].status !== LinkStatus.LINK_EMBEDDED) badLinks++;
        }
        doc.exportFile(ExportFormat.INDESIGN_MARKUP, File(job.output), false);
        return '{"pages":' + doc.pages.length + ',"overset":' + overset +
            ',"bad_fonts":' + badFonts + ',"bad_links":' + badLinks + '}';
    } finally {
        if (doc !== null && doc.isValid) doc.close(SaveOptions.NO);
        app.scriptPreferences.userInteractionLevel = oldInteraction;
    }
}());
