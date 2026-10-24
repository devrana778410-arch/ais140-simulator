package com.ais140.simulator

import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import javax.crypto.Mac
import javax.crypto.spec.SecretKeySpec

/**
 * Configuration for an AIS 140 packet.
 */
data class PacketConfig(
    val imei: String = "864000080862878",
    val vehicleReg: String = "GJ01AC0000",
    val firmware: String = "4.0.27",
    val vendor: String = "TRAXINA",
    val protocol: String = "NMP",
    val latitude: Double = 21.726307,
    val longitude: Double = 73.290024,
    val altitude: Double = 46.0,
    val speed: Double = 0.0,
    val heading: Double = 208.53,
    val satellites: Int = 13,
    val operator: String = "AIRTEL",
    val mcc: String = "404",
    val mnc: String = "05",
    val cellId: String = "16D5",
    val lac: String = "56C5",
    val hmacKey: String = "26bcb9e368440d4a"
)

object Ais140Packet {

    private val dateFmt = SimpleDateFormat("ddMMyyyy", Locale.US)
    private val timeFmt = SimpleDateFormat("HHmmss", Locale.US)
    private val headerDateFmt = SimpleDateFormat("dd-MM-yyyy", Locale.US)
    private val headerTimeFmt = SimpleDateFormat("HH-mm-ss", Locale.US)

    /**
     * Computes HMAC-SHA256 of [body] using [key], returned as a lowercase hex string.
     * Returns empty string if key is blank.
     */
    private fun hmacSha256(key: String, body: String): String {
        if (key.isBlank()) return ""
        return try {
            val mac = Mac.getInstance("HmacSHA256")
            mac.init(SecretKeySpec(key.toByteArray(Charsets.UTF_8), "HmacSHA256"))
            mac.doFinal(body.toByteArray(Charsets.UTF_8))
                .joinToString("") { "%02x".format(it) }
        } catch (e: Exception) {
            ""
        }
    }

    /**
     * Formats latitude for AIS 140: "0DD.MMMMMM,H"
     * e.g. 21.726307 → "021.726307,N"
     */
    private fun formatLat(lat: Double): String {
        val hemi = if (lat >= 0) "N" else "S"
        return "%010.6f,%s".format(Locale.US, Math.abs(lat), hemi)
    }

    /**
     * Formats longitude for AIS 140: "0DD.MMMMMM,H"
     * e.g. 73.290024 → "073.290024,E"
     */
    private fun formatLon(lon: Double): String {
        val hemi = if (lon >= 0) "E" else "W"
        return "%010.6f,%s".format(Locale.US, Math.abs(lon), hemi)
    }

    /**
     * Builds a standard AIS 140 position packet with HMAC-SHA256 signature.
     *
     * Wire packet format:
     *   $<protocol>,<vendor>,<fw>,NR,01,L,<imei>,<reg>,
     *   1,<date8>,<time6>,<lat>,<lon>,<speed>,<heading>,<alt>,
     *   136.7,0.7,0.4,<operator>,0,1,25.8,4.0,0,C,<sats>,<mcc>,<mnc>,<cell>,<lac>,
     *   56C2,16D5,14,5909,16D5,14,37CB,16D5,14,5980,16D5,14,0000,
     *   00,001994,0.80,0.00,0,(0,0,0)*,<HMAC>\r\n
     */
    fun buildPositionPacket(config: PacketConfig): String {
        val now = Date()
        val date8 = dateFmt.format(now)
        val time6 = timeFmt.format(now)

        val body = buildString {
            append("\$${config.protocol},${config.vendor},${config.firmware},")
            append("NR,01,L,")
            append("${config.imei},${config.vehicleReg},")
            append("1,${date8},${time6},")
            append("${formatLat(config.latitude)},${formatLon(config.longitude)},")
            append("${"%.1f".format(Locale.US, config.speed)},")
            append("${"%.2f".format(Locale.US, config.heading)},")
            append("${"%.0f".format(Locale.US, config.altitude)},")
            append("136.7,0.7,0.4,")
            append("${config.operator},0,1,25.8,4.0,0,C,")
            append("${config.satellites},${config.mcc},${config.mnc},")
            append("${config.cellId},${config.lac},")
            // Neighbour cell towers
            append("56C2,16D5,14,5909,16D5,14,37CB,16D5,14,5980,16D5,14,0000,00,")
            append("001994,0.80,0.00,0,(0,0,0)*")
        }

        val hmac = hmacSha256(config.hmacKey, body)
        return if (hmac.isNotEmpty()) "$body,$hmac\r\n" else "$body\r\n"
    }

    /**
     * Builds an AIS 140 login/handshake packet.
     * Format: <date>,<time>\r\nNL,$<protocol>,<vendor>,<fw>,<imei>,<reg>,*<HMAC>
     */
    fun buildLoginPacket(config: PacketConfig): String {
        val now = Date()
        val headerDate = headerDateFmt.format(now)
        val headerTime = headerTimeFmt.format(now)

        val body = "NL,\$${config.protocol},${config.vendor},${config.firmware}," +
                "${config.imei},${config.vehicleReg},*,"
        val hmac = hmacSha256(config.hmacKey, body)
        return "$headerDate,$headerTime\r\n$body$hmac"
    }

    /**
     * Builds an emergency/alert packet.
     */
    fun buildEmergencyPacket(config: PacketConfig): String {
        val now = Date()
        val headerDate = headerDateFmt.format(now)
        val headerTime = headerTimeFmt.format(now)
        val date8 = dateFmt.format(now)
        val time6 = timeFmt.format(now)

        val body = buildString {
            append("EM,\$${config.protocol},${config.vendor},${config.firmware},")
            append("NR,01,L,")
            append("${config.imei},${config.vehicleReg},")
            append("1,${date8},${time6},")
            append("${formatLat(config.latitude)},${formatLon(config.longitude)},")
            append("${"%.1f".format(config.speed)},")
            append("${"%.2f".format(config.heading)},")
            append("${"%.0f".format(config.altitude)},")
            append("136.7,0.7,0.4,")
            append("${config.operator},0,1,25.8,4.0,0,C,")
            append("${config.satellites},${config.mcc},${config.mnc},")
            append("${config.cellId},${config.lac},${config.cellId},56C2,${config.cellId},")
            append("14,5909,${config.cellId},14,37CB,${config.cellId},14,5980,${config.cellId},14,0000,")
            append("00,001994,0.80,0.00,1,(1,0,0)*,")
        }

        val hmac = hmacSha256(config.hmacKey, body)
        return "$headerDate,$headerTime\r\n$body$hmac"
    }
}
