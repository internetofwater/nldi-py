class MediaType(StrEnum):
    """IANA-registered media types used in OGC APIs.

    Media types from the following sources are observed:

        * IANA Media Types Registry
        * RFC 7946: The GeoJSON Format
        * OpenAPI Specification
        * OGC API Standards

    Each media type has a value (the MIME type string) and a description
    documenting its format and usage.
    """

    def __new__(cls, value: str, description: str = ""):
        """Create a new MediaType with value and description."""
        obj = str.__new__(cls, value)
        obj._value_ = value
        obj.description = description
        return obj

    # ========================================================================
    # Common Web Formats (IANA)
    # ========================================================================

    TEXT = "text/plain", "Plain text format"
    HTML = "text/html", "HTML document format"
    JSON = "application/json", "JSON format - RFC 8259"
    XML = "application/xml", "XML format"
    PDF = "application/pdf", "Adobe Portable Document Format"

    # ========================================================================
    # OGC Geospatial Formats
    # ========================================================================

    GEOJSON = (
        "application/geo+json",
        "GeoJSON format - RFC 7946. Used for feature collections and individual features.",
    )

    GML = (
        "application/gml+xml",
        "Geography Markup Language (GML). OGC standard for geospatial vector data in XML.",
    )

    COVERAGEJSON = (
        "application/prs.coverage+json",
        "CoverageJSON format. JSON-based format for spatiotemporal coverage data.",
    )

    GEOTIFF = (
        "image/tiff; application=geotiff",
        "GeoTIFF raster format. OGC standard for georeferenced raster data.",
    )

    PNG = (
        "image/png",
        "PNG image format. Lossless raster image for visual preview.",
    )

    # ========================================================================
    # OpenAPI Specification Formats (Versioned)
    # ========================================================================

    OPENAPI_30_JSON = (
        "application/vnd.oai.openapi+json;version=3.0",
        "OpenAPI 3.0 specification in JSON format",
    )

    OPENAPI_31_JSON = (
        "application/vnd.oai.openapi+json;version=3.1",
        "OpenAPI 3.1 specification in JSON format",
    )

    OPENAPI_30_YAML = (
        "application/vnd.oai.openapi;version=3.0",
        "OpenAPI 3.0 specification in YAML format",
    )

    OPENAPI_31_YAML = (
        "application/vnd.oai.openapi;version=3.1",
        "OpenAPI 3.1 specification in YAML format",
    )

    # ========================================================================
    # Linked Data Formats
    # ========================================================================

    JSONLD = (
        "application/ld+json",
        "JSON-LD (Linked Data) format. JSON-based format for representing linked data.",
    )

    # ========================================================================
    # Binary Geospatial Formats
    # ========================================================================

    FLATGEOBUF = (
        "application/flatgeobuf",
        "FlatGeobuf format. Binary geospatial format optimized for streaming.",
    )

    GEOPARQUET = (
        "application/vnd.apache.parquet",
        "GeoParquet format. Parquet with geospatial extensions.",
    )

    # ========================================================================
    # Error Response Formats
    # ========================================================================

    PROBLEM_JSON = (
        "application/problem+json",
        "RFC 7807 Problem Details for HTTP APIs.",
    )

    # ========================================================================
    # Helper Properties
    # ========================================================================

    @property
    def is_json_based(self) -> bool:
        """Check if this is a JSON-based format."""
        return "+json" in self.value or self.value == "application/json"

    @property
    def is_xml_based(self) -> bool:
        """Check if this is an XML-based format."""
        return "+xml" in self.value or self.value == "application/xml"

    @property
    def is_geospatial(self) -> bool:
        """Check if this is a geospatial format."""
        return self in (
            MediaType.GEOJSON,
            MediaType.GML,
            MediaType.COVERAGEJSON,
            MediaType.GEOTIFF,
            MediaType.PNG,
            MediaType.FLATGEOBUF,
            MediaType.GEOPARQUET,
        )

    @property
    def is_human_readable(self) -> bool:
        """Check if primarily intended for human consumption."""
        return self in (MediaType.HTML, MediaType.TEXT)

    @property
    def is_machine_readable(self) -> bool:
        """Check if primarily intended for machine consumption."""
        return not self.is_human_readable

    @property
    def is_binary(self) -> bool:
        """Check if this is a binary format."""
        return self in (
            MediaType.PDF,
            MediaType.GEOTIFF,
            MediaType.PNG,
            MediaType.FLATGEOBUF,
            MediaType.GEOPARQUET,
        )

    @property
    def is_openapi(self) -> bool:
        """Check if this is an OpenAPI specification format."""
        return self in (
            MediaType.OPENAPI_30_JSON,
            MediaType.OPENAPI_31_JSON,
            MediaType.OPENAPI_30_YAML,
            MediaType.OPENAPI_31_YAML,
        )

    @property
    def category(self) -> str:
        """Return the major media type category (text, application, etc.)."""
        return self.value.split("/")[0]

    @property
    def subtype(self) -> str:
        """Return the media subtype (html, json, geo+json, etc.)."""
        full_subtype = self.value.split("/")[1]
        # Remove parameters like ;version=3.0
        return full_subtype.split(";")[0]

    @property
    def file_extension(self) -> str:
        """Return typical file extension for this media type."""
        extensions = {
            MediaType.TEXT: "txt",
            MediaType.HTML: "html",
            MediaType.JSON: "json",
            MediaType.GEOJSON: "geojson",
            MediaType.XML: "xml",
            MediaType.GML: "gml",
            MediaType.PDF: "pdf",
            MediaType.COVERAGEJSON: "covjson",
            MediaType.GEOTIFF: "tif",
            MediaType.PNG: "png",
            MediaType.JSONLD: "jsonld",
            MediaType.FLATGEOBUF: "fgb",
            MediaType.GEOPARQUET: "parquet",
            MediaType.OPENAPI_30_JSON: "json",
            MediaType.OPENAPI_31_JSON: "json",
            MediaType.OPENAPI_30_YAML: "yaml",
            MediaType.OPENAPI_31_YAML: "yaml",
        }
        return extensions.get(self, "bin")
