__all__ = (
    "modal_button",
    "modal",
    "modal_show",
    "modal_remove",
)

import sys
from typing import Optional, Any

if sys.version_info >= (3, 8):
    from typing import Literal
else:
    from typing_extensions import Literal

from htmltools import tags, Tag, div, HTML, TagChildArg, TagAttrArg

from .._docstring import add_example
from ..session import Session, require_active_session


def modal_button(
    label: TagChildArg, icon: TagChildArg = None, **kwargs: TagChildArg
) -> Tag:
    """
    Creates a button that will dismiss a :func:`modal` (useful when customising the
    ``footer`` of :func:`modal`).

    Parameters
    ----------
    label
        An input label.
    icon
        An icon to appear inline with the button/link.
    kwargs
        Attributes to be applied to the button.

    Returns
    -------
    A UI element

    See Also
    -------
    ~shiny.ui.modal
    ~shiny.ui.modal_show
    ~shiny.ui.modal_remove

    Example
    -------
    See :func:`modal`.
    """
    return tags.button(
        icon,
        label,
        {"class": "btn btn-default"},
        type="button",
        data_dismiss="modal",
        data_bs_dismiss="modal",
        **kwargs
    )


@add_example()
def modal(
    *args: TagChildArg,
    title: Optional[str] = None,
    footer: Any = None,
    size: Literal["m", "s", "l", "xl"] = "m",
    easy_close: bool = False,
    dismiss_button: bool = True,
    fade: bool = True,
    **kwargs: TagAttrArg
) -> Tag:
    """
    Creates the UI for a modal dialog, using Bootstrap's modal class. Modals are
    typically used for showing important messages, or for presenting UI that requires
    input from the user, such as a user name and/or password input.

    Parameters
    ----------
    args
        UI elements for the body of the modal.
    title
        An optional title for the modal dialog.
    footer
        UI for footer. Use ``None`` for no footer.
    size
        One of "s" for small, "m" (the default) for medium, or "l" for large.
    easy_close
        If ``True``, the modal dialog can be dismissed by clicking outside the dialog
        box, or be pressing the Escape key. If ``False`` (the default), the modal dialog
        can't be dismissed in those ways; instead it must be dismissed by clicking on a
        ``modal_button()``, or from a call to ``modal_remove()`` on the server.
    dismiss_button
        If ``True``, adds a Dismiss button to the footer of the modal.
    fade
        If ``False``, the modal dialog will have no fade-in animation (it will simply
        appear rather than fade in to view).
    kwargs
        Attributes to be applied to the modal's body tag.

    Returns
    -------
    A UI element

    See Also
    -------
    ~shiny.ui.modal_show
    ~shiny.ui.modal_remove
    ~shiny.ui.modal_button
    """

    title_div = None
    if title:
        title_div = div(tags.h4(title, class_="modal-title"), class_="modal-header")

    if footer or dismiss_button:
        footer = div(
            footer,
            modal_button("Dismiss") if dismiss_button else None,
            class_="modal-footer",
        )

    dialog = div(
        div(
            title_div,
            div({"class": "modal-body"}, *args, **kwargs),
            footer,
            class_="modal-content",
        ),
        class_="modal-dialog"
        + ({"s": " modal-sm", "l": " modal-lg", "xl": " modal-xl"}.get(size, "")),
    )

    # jQuery plugin doesn't work in Bootstrap 5, but vanilla JS doesn't work in Bootstrap 4 :sob:
    js = "\n".join(
        [
            "if (window.bootstrap && !window.bootstrap.Modal.VERSION.match(/^4\\. /)) {",
            "  var modal=new bootstrap.Modal(document.getElementById('shiny-modal'))",
            "  modal.show()",
            "} else {",
            "  $('#shiny-modal').modal().focus()",
            "}",
        ]
    )

    backdrop = None if easy_close else "static"
    keyboard = None if easy_close else "false"

    return div(
        dialog,
        tags.script(HTML(js)),
        id="shiny-modal",
        class_="modal fade" if fade else "modal",
        tabindex="-1",
        data_backdrop=backdrop,
        data_bs_backdrop=backdrop,
        data_keyboard=keyboard,
        data_bs_keyboard=keyboard,
    )


def modal_show(modal: Tag, session: Optional[Session] = None) -> None:
    """
    Show a modal dialog.

    Parameters
    ----------
    modal
        Typically a :func:`modal` instance.
    session
        A :class:`~shiny.Session` instance. If not provided, it is inferred via
       :func:`~shiny.session.get_current_session`.

    See Also
    -------
    ~shiny.ui.modal_remove
    ~shiny.ui.modal

    Example
    -------
    See :func:`modal`.
    """
    session = require_active_session(session)
    msg = session._process_ui(modal)
    session._send_message_sync({"modal": {"type": "show", "message": msg}})


def modal_remove(session: Optional[Session] = None) -> None:
    """
    Remove a modal dialog.

    Parameters
    ----------
    session
        A :class:`~shiny.Session` instance. If not provided, it is inferred via
       :func:`~shiny.session.get_current_session`.

    See Also
    -------
    ~shiny.ui.modal_show
    ~shiny.ui.modal

    Example
    -------
    See :func:`modal`.
    """
    session = require_active_session(session)
    session._send_message_sync({"modal": {"type": "remove", "message": None}})
