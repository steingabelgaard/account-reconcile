import ast

from odoo import models


class AccountJournal(models.Model):

    _inherit = "account.journal"

    def action_open_reconcile(self):
        # Open reconciliation view for bank statements belonging to this journal
        bank_stmt = (
            self.env["account.bank.statement"]
            .search([("journal_id", "in", self.ids)])
            .mapped("line_ids")
        )
        return {
            "type": "ir.actions.client",
            "tag": "bank_statement_reconciliation_view",
            "context": {
                "statement_line_ids": bank_stmt.ids,
                "company_ids": self.mapped("company_id").ids,
            },
        }

    def action_open_reconcile_to_check(self):
        self.ensure_one()
        ids = self.to_check_ids().ids
        action_context = {
            "show_mode_selector": False,
            "company_ids": self.mapped("company_id").ids,
            "suspense_moves_mode": True,
            "statement_line_ids": ids,
        }
        return {
            "type": "ir.actions.client",
            "tag": "bank_statement_reconciliation_view",
            "context": action_context,
        }

    def open_action_ext(self):
        """return action based on type for related journals"""
        self.ensure_one()
        action_name = self._select_action_to_open()

        # Set 'account.' prefix if missing.
        if "." not in action_name:
            action_name = "account.%s" % action_name

        action = self.env["ir.actions.act_window"]._for_xml_id(action_name)

        context = self._context.copy()
        if "context" in action and isinstance(action["context"], str):
            context.update(ast.literal_eval(action["context"]))
        else:
            context.update(action.get("context", {}))
        action["context"] = context
        action["context"].update(
            {
                "default_journal_id": self.id,
                "search_default_journal_id": self.id,
            }
        )

        domain_type_field = (
            action["res_model"] == "account.move.line"
            and "move_id.move_type"
            or "move_type"
        )  # The model can be either account.move or account.move.line

        # Override the domain only if the action was not explicitly specified
        # in order to keep the original action domain.
        if not self._context.get("action_name"):
            if self.type == "sale":
                action["domain"] = [
                    (
                        domain_type_field,
                        "in",
                        ("out_invoice", "out_refund", "out_receipt"),
                    )
                ]
            elif self.type == "purchase":
                action["domain"] = [
                    (
                        domain_type_field,
                        "in",
                        ("in_invoice", "in_refund", "in_receipt", "entry"),
                    )
                ]

        return action
