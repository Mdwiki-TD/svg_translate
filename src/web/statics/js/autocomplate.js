$(document).ready(function() {
    $("#title").autocomplete({
            source: function(request, response) {
                // make AJAX request to Wikipedia API
                $.ajax({
                    url: "https://commons.wikimedia.org/w/api.php",
                    headers: {
                        'Api-User-Agent': "Translation Dashboard/1.0 (https://mdwiki.toolforge.org/; tools.mdwiki@toolforge.org)"
                    },
                    dataType: "jsonp",
                    data: {
                        action: "query",
                        list: "prefixsearch",
                        format: "json",
                        pssearch: request.term,
                        psnamespace: 0,
                        psbackend: "CirrusSearch",
                        cirrusUseCompletionSuggester: "yes"
                    },
                    success: function(data) {
                        // extract titles from API response and pass to autocomplete
                        response($.map(data.query.prefixsearch, function(item) {
                            return item.title;
                        }));
                    }
                });
            }
        });
});
