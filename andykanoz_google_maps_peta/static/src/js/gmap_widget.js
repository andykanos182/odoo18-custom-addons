/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, useRef, onMounted, onWillUnmount, useState } from "@odoo/owl";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { useService } from "@web/core/utils/hooks";

/**
 * GMapWidget — OWL Widget for Google Maps in Odoo 18 Backend
 * Menampilkan peta interaktif di form view res.partner (Partner Assignment tab)
 * Marker bisa di-drag untuk update Lat/Long otomatis.
 */
class GMapWidget extends Component {
    static template = "andykanoz_google_maps_peta.GMapWidget";
    static props = { ...standardFieldProps };

    setup() {
        this.mapRef = useRef("gmap_container");
        this.orm = useService("orm");
        this.state = useState({
            mapLoaded: false,
            errorMsg: "",
        });
        this.map = null;
        this.marker = null;
        this._apiLoaded = false;

        onMounted(async () => {
            await this._loadGoogleMapsAPI();
            this._initMap();
        });

        onWillUnmount(() => {
            this.map = null;
            this.marker = null;
        });
    }

    get lat() {
        return this.props.record.data.partner_latitude || 0;
    }

    get lng() {
        return this.props.record.data.partner_longitude || 0;
    }

    async _loadGoogleMapsAPI() {
        // Cek apakah Google Maps sudah loaded
        if (window.google && window.google.maps) {
            this._apiLoaded = true;
            return;
        }

        // Ambil API key dari config parameter via ORM
        try {
            const result = await this.orm.call(
                "ir.config_parameter",
                "get_param",
                ["base_geolocalize.google_map_api_key"]
            );

            if (!result) {
                this.state.errorMsg = "Google Maps API Key belum diatur. Buka Settings → Integrations → Geolocation.";
                return;
            }

            // Load Google Maps JS API
            await new Promise((resolve, reject) => {
                const script = document.createElement("script");
                script.src = `https://maps.googleapis.com/maps/api/js?key=${result}&libraries=places`;
                script.async = true;
                script.defer = true;
                script.onload = () => {
                    this._apiLoaded = true;
                    resolve();
                };
                script.onerror = () => {
                    this.state.errorMsg = "Gagal memuat Google Maps API. Periksa API Key Anda.";
                    reject();
                };
                document.head.appendChild(script);
            });
        } catch (e) {
            this.state.errorMsg = "Error loading Google Maps: " + (e.message || e);
        }
    }

    _initMap() {
        if (!this._apiLoaded || !this.mapRef.el) return;

        const DEFAULT_LAT = -8.6705;
        const DEFAULT_LNG = 115.2126;
        const DEFAULT_ZOOM = 15;

        const initLat = (this.lat !== 0) ? this.lat : DEFAULT_LAT;
        const initLng = (this.lng !== 0) ? this.lng : DEFAULT_LNG;

        const center = { lat: initLat, lng: initLng };

        // Buat peta
        this.map = new google.maps.Map(this.mapRef.el, {
            center: center,
            zoom: DEFAULT_ZOOM,
            mapTypeControl: true,
            streetViewControl: true,
            fullscreenControl: true,
            zoomControl: true,
        });

        // Buat marker draggable
        this.marker = new google.maps.Marker({
            position: center,
            map: this.map,
            draggable: true,
            animation: google.maps.Animation.DROP,
            title: "Drag untuk memilih lokasi",
        });

        // Event: drag marker
        this.marker.addListener("dragend", (event) => {
            const lat = event.latLng.lat();
            const lng = event.latLng.lng();
            this._updateCoordinates(lat, lng);
        });

        // Event: klik peta
        this.map.addListener("click", (event) => {
            const lat = event.latLng.lat();
            const lng = event.latLng.lng();
            this.marker.setPosition(event.latLng);
            this._updateCoordinates(lat, lng);
        });

        this.state.mapLoaded = true;

        // Fix map resize setelah render
        setTimeout(() => {
            if (this.map) {
                google.maps.event.trigger(this.map, "resize");
                this.map.setCenter(center);
            }
        }, 300);
    }

    async _updateCoordinates(lat, lng) {
        // Update field di record Odoo
        const record = this.props.record;
        await record.update({
            partner_latitude: lat,
            partner_longitude: lng,
        });
    }

    onClickMyLocation() {
        if (!navigator.geolocation) {
            this.state.errorMsg = "Browser tidak mendukung geolocation.";
            return;
        }

        this.state.errorMsg = "";

        navigator.geolocation.getCurrentPosition(
            (pos) => {
                const lat = pos.coords.latitude;
                const lng = pos.coords.longitude;
                const latLng = new google.maps.LatLng(lat, lng);

                if (this.map && this.marker) {
                    this.map.setCenter(latLng);
                    this.map.setZoom(17);
                    this.marker.setPosition(latLng);
                    this.marker.setAnimation(google.maps.Animation.DROP);
                    this._updateCoordinates(lat, lng);
                }
            },
            (err) => {
                let msg = "Tidak dapat mendeteksi lokasi.";
                if (err.code === 1) msg = "Akses lokasi ditolak oleh browser.";
                if (err.code === 2) msg = "Lokasi tidak tersedia.";
                if (err.code === 3) msg = "Timeout. Coba lagi.";
                this.state.errorMsg = msg;
            },
            { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
        );
    }
}

// Register widget di registry
registry.category("fields").add("gmap_marker_widget", {
    component: GMapWidget,
    supportedTypes: ["float"],
});
