package com.ais140.simulator

import kotlin.math.atan2
import kotlin.math.cos
import kotlin.math.sin
import kotlin.math.sqrt

data class RtoItem(
    val code: String,
    val name: String,
    val lat: Double,
    val lon: Double
) {
    override fun toString(): String = "$code – $name"
}

object RtoData {
    val RTO_LIST = listOf(
        RtoItem("GJ-01", "Ahmedabad (West - Subhash Bridge)", 23.061700, 72.580200),
        RtoItem("GJ-02", "Mehsana", 23.588000, 72.369300),
        RtoItem("GJ-03", "Rajkot", 22.303900, 70.802200),
        RtoItem("GJ-04", "Bhavnagar", 21.764500, 72.151900),
        RtoItem("GJ-05", "Surat (City)", 21.170200, 72.831100),
        RtoItem("GJ-06", "Vadodara (City)", 22.307200, 73.181200),
        RtoItem("GJ-07", "Nadiad (Kheda)", 22.691600, 72.863400),
        RtoItem("GJ-08", "Palanpur (Banaskantha)", 24.171800, 72.434600),
        RtoItem("GJ-09", "Himmatnagar (Sabarkantha)", 23.597900, 72.969800),
        RtoItem("GJ-10", "Jamnagar", 22.470700, 70.057700),
        RtoItem("GJ-11", "Junagadh", 21.522200, 70.457900),
        RtoItem("GJ-12", "Bhuj (Kutch)", 23.242000, 69.666900),
        RtoItem("GJ-13", "Surendranagar", 22.727200, 71.648700),
        RtoItem("GJ-14", "Amreli", 21.604000, 71.221800),
        RtoItem("GJ-15", "Valsad", 20.611600, 72.928900),
        RtoItem("GJ-16", "Bharuch", 21.705100, 72.995900),
        RtoItem("GJ-17", "Godhra (Panchmahal)", 22.775800, 73.614900),
        RtoItem("GJ-18", "Gandhinagar", 23.215600, 72.636900),
        RtoItem("GJ-19", "Bardoli (Surat East)", 21.121500, 73.111800),
        RtoItem("GJ-20", "Dahod", 22.834700, 74.254600),
        RtoItem("GJ-21", "Navsari", 20.946700, 72.952000),
        RtoItem("GJ-22", "Rajpipla (Narmada)", 21.870300, 73.502700),
        RtoItem("GJ-23", "Anand", 22.564500, 72.928900),
        RtoItem("GJ-24", "Patan", 23.849400, 72.126600),
        RtoItem("GJ-25", "Porbandar", 21.641700, 69.629300),
        RtoItem("GJ-26", "Vyara (Tapi)", 21.112100, 73.393400),
        RtoItem("GJ-27", "Ahmedabad (East - Vastral)", 22.998600, 72.646800),
        RtoItem("GJ-28", "Surat (Rural - Pal)", 21.195900, 72.775300),
        RtoItem("GJ-29", "Vadodara (Rural)", 22.315000, 73.200000),
        RtoItem("GJ-30", "Ahwa (Dang)", 20.758400, 73.687400),
        RtoItem("GJ-31", "Modasa (Aravalli)", 23.461600, 73.300500),
        RtoItem("GJ-32", "Veraval (Gir Somnath)", 20.907700, 70.367600),
        RtoItem("GJ-33", "Botad", 22.169800, 71.665900),
        RtoItem("GJ-34", "Chhota Udepur", 22.304100, 74.014700),
        RtoItem("GJ-35", "Lunawada (Mahisagar)", 23.132500, 73.618600),
        RtoItem("GJ-36", "Morbi", 22.817300, 70.837300),
        RtoItem("GJ-37", "Khambhalia (Devbhumi Dwarka)", 22.205600, 69.658300),
        RtoItem("GJ-38", "Bavla (Ahmedabad Rural)", 22.834400, 72.361900),
        RtoItem("DD-01", "Daman", 20.397400, 72.832800),
        RtoItem("DD-02", "Diu", 20.714400, 70.987400),
        RtoItem("DN-01", "Silvassa (Dadra & Nagar Haveli)", 20.273300, 72.998600),
        RtoItem("DN-09", "Dadra & Nagar Haveli (Silvassa)", 20.273300, 72.998600)
    )

    private val rtoMap = RTO_LIST.associateBy { it.code }

    fun getByCode(code: String): RtoItem? = rtoMap[code]

    fun findNearestRto(lat: Double, lon: Double): RtoItem {
        fun haversineKm(lat1: Double, lon1: Double, lat2: Double, lon2: Double): Double {
            val r = 6371.0
            val dLat = Math.toRadians(lat2 - lat1)
            val dLon = Math.toRadians(lon2 - lon1)
            val a = sin(dLat / 2) * sin(dLat / 2) +
                    cos(Math.toRadians(lat1)) * cos(Math.toRadians(lat2)) *
                    sin(dLon / 2) * sin(dLon / 2)
            val c = 2 * atan2(sqrt(a), sqrt(1 - a))
            return r * c
        }

        return RTO_LIST.minByOrNull { haversineKm(lat, lon, it.lat, it.lon) } ?: RTO_LIST[15]
    }
}
