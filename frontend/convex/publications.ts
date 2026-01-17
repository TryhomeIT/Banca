import { v } from "convex/values";
import { query, mutation } from "./_generated/server";

export const list = query({
  args: {
    category: v.optional(v.string()),
  },
  handler: async (ctx, args) => {
    if (args.category) {
      return await ctx.db
        .query("publications")
        .withIndex("by_category", (q) => q.eq("category", args.category))
        .order("desc")
        .collect();
    }
    return await ctx.db
      .query("publications")
      .withIndex("by_publication_date")
      .order("desc")
      .collect();
  },
});

export const add = mutation({
  args: {
    title: v.string(),
    filename: v.string(),
    original_filename: v.string(),
    thumbnail_path: v.optional(v.string()),
    file_path: v.string(),
    page_count: v.number(),
    file_size: v.number(),
    category: v.optional(v.string()),
    publication_date: v.optional(v.string()),
    external_id: v.optional(v.number()),
  },
  handler: async (ctx, args) => {
    const now = new Date().toISOString();
    
    // Check if it already exists by filename to avoid duplicates
    const existing = await ctx.db
      .query("publications")
      .filter((q) => q.eq(q.field("filename"), args.filename))
      .first();
      
    if (existing) {
      return await ctx.db.patch(existing._id, {
        ...args,
        updated_at: now,
      });
    }

    return await ctx.db.insert("publications", {
      ...args,
      created_at: now,
      updated_at: now,
    });
  },
});

export const clearAll = mutation({
  args: {},
  handler: async (ctx) => {
    const all = await ctx.db.query("publications").collect();
    for (const doc of all) {
      await ctx.db.delete(doc._id);
    }
    return all.length;
  },
});
