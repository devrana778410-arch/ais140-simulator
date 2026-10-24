package com.ais140.simulator

import java.net.URLDecoder
import java.util.regex.Pattern

/**
 * Universal extractor for Google Maps and WhatsApp location links in Android.
 * Extracts (latitude, longitude) from shared URLs, geo URIs, and raw coordinates.
 */
object GeoLinkParser {

    fun extractCoordinates(raw: String?): Pair<Double, Double>? {
        if (raw.isNullOrBlank()) return null

        val text = try {
            URLDecoder.decode(raw.trim(), "UTF-8")
        } catch (_: Exception) {
            raw.trim()
        }

        // 1. Query parameters: ?q=lat,lon or &q=lat,lon or query=lat,lon or &ll=lat,lon
        val pQuery = Pattern.compile("[?&](?:q|query|ll)=(-?\\d{1,2}\\.\\d+)\\s*,\\s*(-?\\d{1,3}\\.\\d+)")
        val mQuery = pQuery.matcher(text)
        if (mQuery.find()) {
            val lat = mQuery.group(1)?.toDoubleOrNull()
            val lon = mQuery.group(2)?.toDoubleOrNull()
            if (lat != null && lon != null) return Pair(lat, lon)
        }

        // 2. Path format: /maps/@lat,lon
        val pAt = Pattern.compile("@(-?\\d{1,2}\\.\\d+)\\s*,\\s*(-?\\d{1,3}\\.\\d+)")
        val mAt = pAt.matcher(text)
        if (mAt.find()) {
            val lat = mAt.group(1)?.toDoubleOrNull()
            val lon = mAt.group(2)?.toDoubleOrNull()
            if (lat != null && lon != null) return Pair(lat, lon)
        }

        // 3. geo URI: geo:lat,lon
        val pGeo = Pattern.compile("geo:(-?\\d{1,2}\\.\\d+)\\s*,\\s*(-?\\d{1,3}\\.\\d+)")
        val mGeo = pGeo.matcher(text)
        if (mGeo.find()) {
            val lat = mGeo.group(1)?.toDoubleOrNull()
            val lon = mGeo.group(2)?.toDoubleOrNull()
            if (lat != null && lon != null) return Pair(lat, lon)
        }

        // 4. Raw coordinate pair fallback
        val pRaw = Pattern.compile("\\b(-?\\d{1,2}\\.\\d{3,})\\s*,\\s*(-?\\d{1,3}\\.\\d{3,})\\b")
        val mRaw = pRaw.matcher(text)
        if (mRaw.find()) {
            val lat = mRaw.group(1)?.toDoubleOrNull()
            val lon = mRaw.group(2)?.toDoubleOrNull()
            if (lat != null && lon != null && lat in -90.0..90.0 && lon in -180.0..180.0) {
                return Pair(lat, lon)
            }
        }

        return null
    }
}
