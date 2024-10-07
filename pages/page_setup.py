from nicegui import ui


def font_setup():
    ui.add_css(
        """
        @font-face {
            font-family: "Custom";
            src: url("/fonts/NotoSansTC-VariableFont_wght.ttf") format("truetype");
        }
        body {
            font-family: "Custom", sans-serif;
        }
        .ag-theme-balham {
            --ag-font-family: "Custom", sans-serif !important;
        }
        """
    )


def style_setup(
    color: bool = True,
    center_content: bool = True,
    gap: bool = True,
    thick_button: bool = True,
    no_btn_shadow: bool = True,
    responsive_qcard: bool = True,
    responsive_ag: bool = False,
    dense_card: bool = False,
    dynamic_scroll_padding: bool = False,
    dense_select: bool = False,
):
    if color:
        ui.colors(primary="#a67b5b")
        ui.add_css(
            """
        body {
            background-color:#faf7f5;
        }
        """
        )
    # .nicegui-content has flex property and is a column
    # Center the contents in it (for responsive adjustment of w-max)
    if center_content:
        ui.add_css(
            """
        .nicegui-content {
            justify-content: start;
            align-items: center;
        }
    """
        )
    # Adjust nicegui-default-gap to 10px on 16px standard rem
    # Adjust quasar icon on_right/left margin to 0 (effectively remove the gap between icon and text)
    if gap:
        ui.add_css(
            """
        :root {
            --nicegui-default-gap: 0.625rem
        }
        .on-right {
            margin-left: 0px
        }
        .on-left {
            margin-right: 0px
        }
        """
        )
    # Make the default Q-button outline 2px instead of 1px thick
    if thick_button:
        ui.add_css(
            """
        .q-btn--outline:before {
            border: 2px solid currentColor !important;
        }
        """
        )
    # Remove all box shadow on q-buttons
    if no_btn_shadow:
        ui.add_css(
            """
            .q-btn:before {
        box-shadow: none !important;
    }
    """
        )
    # Enlarge ag grid text above md(768px)
    if responsive_ag:
        ui.add_css(
            """
        .ag-theme-balham {
            --ag-font-size: 13px !important;
        }
        @media (min-width: 768px) {
            .ag-theme-balham {
                --ag-font-size: 16px !important;
            }
        }
    """
        )
    if responsive_qcard:
        ui.add_css(
            """
        .q-table > thead > tr > th {
            font-size: 13px !important;
        }
        .q-table > tbody > tr > td {
            font-size: 14px !important;
        }
        @media (min-width: 768px) {
            .q-table > thead > tr > th {
                font-size: 15px !important;
            }
            .q-table > tbody > tr > td {
                font-size: 16px !important;
            }
        }
    """
        )
    # Overwrite q-table default padding to make it desner vertically
    # Making the .nicegui-content fill the screen then apply flex-1 to scroll area
    if dense_card:
        ui.add_css(
            """
        .q-table td:first-child,
        .q-table th:first-child {
            padding-left: 0.5rem !important;
        }
        .q-table td:last-child,
        .q-table th:last-child {
            padding-right: 0.5rem !important;
        }
        .q-table td,
        .q-table th {
            padding-left: 0.25rem !important; padding-right: 0.25rem !important;
        }
        .nicegui-content {
            height: 100vh;
        }
        .q-scrollarea__content {
            padding-top: 0.125rem !important; padding-bottom: 0.125rem !important; padding-left: 0.125rem !important;
        }
        """
        )
    # Listen to the presence of q-scrollarea__bar--invisible class on the scrollbar
    # And make the right padding of scroll content smaller to extend the content (GridOfCards)
    if dynamic_scroll_padding:
        ui.add_head_html(
            """
        <script>
        function observeScrollbar() {
            const scrollbar = document.querySelector('.q-scrollarea__bar');

            if (scrollbar) {
                const observer = new MutationObserver((mutations) => {
                    mutations.forEach((mutation) => {
                        if (mutation.attributeName === 'class') {
                            const content = document.querySelector('.q-scrollarea__content');
                            if (scrollbar.classList.contains('q-scrollarea__bar--invisible')) {
                                content.style.paddingRight = '2px';
                            } else {
                                content.style.paddingRight = '16px';
                            }
                        }
                    });
                });

                observer.observe(scrollbar, { attributes: true });
            }
        }

        document.addEventListener('DOMContentLoaded', observeScrollbar);
        </script>
        """
        )
        # Make q_select items and values denser and smaller
        if dense_select:
            ui.add_css(
                """
            .q-field__native span, .q-field__native input {
                font-size: 0.75rem;
            }
            .q-item span {
                font-size: 0.75rem;
            }
            .q-item {
                padding-left: 0.5rem;
                padding-right: 0.5rem;
            }
            """
            )
