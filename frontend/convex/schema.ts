import { defineSchema, defineTable } from "convex/server";
import { v } from "convex/values";

export default defineSchema({
  publications: defineTable({
    title: v.string(),
    filename: v.string(),
    original_filename: v.string(),
    thumbnail_path: v.optional(v.string()),
    file_path: v.string(),
    page_count: v.number(),
    file_size: v.number(),
    category: v.optional(v.string()),
    publication_date: v.optional(v.string()), // ISO date string
    created_at: v.string(), // ISO date string
    updated_at: v.string(), // ISO date string
    external_id: v.optional(v.number()), // To link back to SQLite if needed
  }).index("by_category", ["category", "publication_date"])
    .index("by_publication_date", ["publication_date"]),
    
  system_status: defineTable({
    is_processing: v.boolean(),
    current_task: v.optional(v.string()),
    last_update: v.string(),
  }),
});
