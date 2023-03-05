window.dashExtensions = Object.assign({}, window.dashExtensions, {
    default: {
        function0: function(feature, latlng) {
            return L.circleMarker(latlng, {
                radius: 8,
                weight: 1,
                color: feature.properties.color,
                fillColor: feature.properties.color,
                opacity: 1,
                fillOpacity: 1
            });
        },
        function1: function(feature, context) {
            return {
                color: feature.properties.color,
                opacity: 0.7
            };
        }
    }
});